import os
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from starlette.requests import Request

from backend.services.gemini_service import (
    generate,
    is_non_retryable_error,
    get_configured_model,
    get_gemini_service_status,
)
from backend.services.auth.jwt_service import (
    validate_jwt_secrets_config,
    get_jwt_secret_key,
    create_access_token,
    DEFAULT_DEV_SECRET,
)
from backend.services.auth.cors_config import parse_cors_origins
from backend.app import app
from backend.services.security.rate_limiter import extract_client_identifier


# ==============================================================================
# A. GEMINI MODEL CONFIGURATION AND RELIABILITY TESTS
# ==============================================================================

def test_gemini_model_configuration():
    """Validates GEMINI_MODEL fallback and environment variable configuration."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GEMINI_MODEL", None)
        assert get_configured_model() == "gemini-3.8-flash"

    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-2.5-flash"}):
        assert get_configured_model() == "gemini-2.5-flash"

    with patch.dict(os.environ, {"GEMINI_MODEL": "invalid-model"}):
        # Falls back to default on unsupported model
        assert get_configured_model() == "gemini-3.8-flash"


def test_is_non_retryable_error():
    """Identifies 429 quota exhaustion, 404, 403, and invalid argument errors as non-retryable."""
    assert is_non_retryable_error(Exception("429 Resource has been exhausted (e.g. check quota)"))
    assert is_non_retryable_error(Exception("404 NOT_FOUND: model not found"))
    assert is_non_retryable_error(Exception("RESOURCE_EXHAUSTED: quota exceeded"))
    assert is_non_retryable_error(Exception("API_KEY_INVALID"))
    # Generic network error is retryable
    assert not is_non_retryable_error(Exception("Connection reset by peer"))
    assert not is_non_retryable_error(Exception("503 Service Unavailable"))


def test_generate_quota_exhaustion_does_not_retry():
    """HTTP 429 quota exhaustion immediately returns None without wasteful retries."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception(
        "429 Resource has been exhausted (check quota for your tier)"
    )

    with patch("backend.services.gemini_service.get_client", return_value=mock_client), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
        result = generate("Generate trip for Paris", max_retries=3)
        assert result is None
        # Must only call ONCE, zero wasteful retries
        assert mock_client.models.generate_content.call_count == 1


def test_generate_transient_error_retries_and_succeeds():
    """Transient 503 errors trigger bounded retry and succeed when service recovers."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"status": "ok", "destination": "Tokyo"}'
    # Fail first call with 503, succeed on second call
    mock_client.models.generate_content.side_effect = [
        Exception("503 Service Unavailable"),
        mock_response,
    ]

    with patch("backend.services.gemini_service.get_client", return_value=mock_client), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}), \
         patch("time.sleep", return_value=None):
        result = generate("Generate trip for Tokyo", max_retries=2)
        assert result == {"status": "ok", "destination": "Tokyo"}
        assert mock_client.models.generate_content.call_count == 2


def test_generate_parses_markdown_code_fences():
    """Markdown code fences (```json ... ```) are cleanly stripped and parsed."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "```json\n{\"destination\": \"Rome\", \"days\": []}\n```"
    mock_client.models.generate_content.return_value = mock_response

    with patch("backend.services.gemini_service.get_client", return_value=mock_client), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
        result = generate("Generate trip for Rome")
        assert result == {"destination": "Rome", "days": []}


def test_planner_fallback_itinerary_when_gemini_fails():
    """When Gemini is unavailable, planner generates a structured fallback itinerary rather than failing or returning empty days."""
    test_client = TestClient(app)

    # Force Gemini to fail by mocking generate to return None
    with patch("backend.routes.planner.generate", return_value=None):
        response = test_client.post(
            "/planner/",
            json={
                "source": "Bengaluru",
                "destination": "Goa",
                "days": 2,
                "travel_mode": "car",
                "travelers": [
                    {
                        "name": "Alex",
                        "interests": ["beaches"],
                        "budget": "medium",
                        "pace": "moderate",
                    }
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "itinerary" in data
        itinerary = data["itinerary"]
        assert "days" in itinerary
        assert len(itinerary["days"]) == 2
        assert itinerary.get("is_fallback") is True
        assert data.get("ai_generation", {}).get("status") == "fallback"


# ==============================================================================
# B. PRODUCTION CONFIGURATION & STARTUP VALIDATION TESTS
# ==============================================================================

def test_production_mode_requires_jwt_secret():
    """Production mode (AUTH_DEV_MODE=false) raises RuntimeError if JWT_SECRET_KEY is missing or empty."""
    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "JWT_SECRET_KEY": ""}):
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is required"):
            validate_jwt_secrets_config()


def test_production_mode_rejects_default_dev_secret():
    """Production mode (AUTH_DEV_MODE=false) rejects committed development default secret."""
    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "JWT_SECRET_KEY": DEFAULT_DEV_SECRET}):
        with pytest.raises(RuntimeError, match="cannot be the committed development default secret"):
            validate_jwt_secrets_config()


def test_production_mode_rejects_short_secret():
    """Production mode (AUTH_DEV_MODE=false) rejects keys with fewer than 32 characters."""
    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "JWT_SECRET_KEY": "short-secret-key-123"}):
        with pytest.raises(RuntimeError, match="must be at least 32 characters long"):
            validate_jwt_secrets_config()


def test_production_mode_accepts_valid_secret():
    """Production mode (AUTH_DEV_MODE=false) accepts valid 32+ character secrets."""
    valid_key = "a" * 64
    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "JWT_SECRET_KEY": valid_key}):
        assert get_jwt_secret_key() == valid_key


def test_production_mode_requires_explicit_cors_origins():
    """Production mode (AUTH_DEV_MODE=false) rejects missing, empty, or wildcard CORS origins."""
    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "ALLOWED_ORIGINS": ""}):
        with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS environment variable is required"):
            parse_cors_origins()

    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "ALLOWED_ORIGINS": "*"}):
        with pytest.raises(RuntimeError, match="Wildcard '\\*' in ALLOWED_ORIGINS is not permitted"):
            parse_cors_origins()

    with patch.dict(os.environ, {"AUTH_DEV_MODE": "false", "ALLOWED_ORIGINS": "https://app.example.com"}):
        origins = parse_cors_origins()
        assert origins == ["https://app.example.com"]


# ==============================================================================
# C. RATE LIMITER CLIENT IDENTIFIER SECURITY TESTS
# ==============================================================================

def test_extract_client_identifier_rejects_untrusted_x_user_id():
    """Untrusted X-User-ID headers without valid Bearer tokens fall back to client IP."""
    scope = {
        "type": "http",
        "headers": [
            (b"x-user-id", b"attacker_forged_id"),
            (b"x-forwarded-for", b"198.51.100.25"),
        ],
        "client": ("198.51.100.25", 12345),
    }
    request = Request(scope)
    identifier = extract_client_identifier(request)
    # MUST NOT be usr:attacker_forged_id
    assert identifier == "ip:198.51.100.25"


def test_extract_client_identifier_uses_verified_token():
    """Cryptographically valid Bearer token provides verified usr:<sub_id> key."""
    token = create_access_token("verified_traveler_42")
    scope = {
        "type": "http",
        "headers": [
            (b"authorization", f"Bearer {token}".encode("utf-8")),
            (b"x-user-id", b"verified_traveler_42"),
            (b"x-forwarded-for", b"198.51.100.25"),
        ],
        "client": ("198.51.100.25", 12345),
    }
    request = Request(scope)
    identifier = extract_client_identifier(request)
    assert identifier == "usr:verified_traveler_42"


def test_extract_client_identifier_rejects_mismatched_token_and_header():
    """Token subject mismatch with X-User-ID header falls back to IP to prevent confused-deputy attacks."""
    token = create_access_token("alice_user")
    scope = {
        "type": "http",
        "headers": [
            (b"authorization", f"Bearer {token}".encode("utf-8")),
            (b"x-user-id", b"bob_spoofed_user"),
            (b"x-forwarded-for", b"198.51.100.25"),
        ],
        "client": ("198.51.100.25", 12345),
    }
    request = Request(scope)
    identifier = extract_client_identifier(request)
    # Must NOT give bob_spoofed_user bucket
    assert identifier == "ip:198.51.100.25"


def test_extract_client_identifier_rejects_spoofed_forwarded_for_from_untrusted_proxy():
    """When the client socket is NOT a trusted proxy, spoofed X-Forwarded-For is ignored."""
    scope = {
        "type": "http",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.199"),
        ],
        "client": ("198.51.100.55", 12345),
    }
    request = Request(scope)

    with patch.dict(os.environ, {"TRUST_PROXY_HEADERS": "false", "TRUSTED_PROXIES": "127.0.0.1"}):
        identifier = extract_client_identifier(request)
        # Must ignore spoofed 203.0.113.199 and use direct socket host 198.51.100.55
        assert identifier == "ip:198.51.100.55"


def test_extract_client_identifier_honors_forwarded_for_when_proxy_trusted():
    """When the client is a trusted proxy or TRUST_PROXY_HEADERS=true, X-Forwarded-For is used."""
    scope = {
        "type": "http",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.199, 10.0.0.1"),
        ],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    # Trust via loopback proxy
    with patch.dict(os.environ, {"TRUST_PROXY_HEADERS": "false", "TRUSTED_PROXIES": "127.0.0.1"}):
        identifier = extract_client_identifier(request)
        assert identifier == "ip:203.0.113.199"

    # Trust via TRUST_PROXY_HEADERS=true
    scope["client"] = ("10.0.0.2", 12345)
    req2 = Request(scope)
    with patch.dict(os.environ, {"TRUST_PROXY_HEADERS": "true"}):
        identifier2 = extract_client_identifier(req2)
        assert identifier2 == "ip:203.0.113.199"

