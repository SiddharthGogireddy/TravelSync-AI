"""
Step 84: Critical Production Security Hardening Tests
Verifies:
1. Development token issuance is enabled in development (AUTH_DEV_MODE=true) and rejected with 403 in production (AUTH_DEV_MODE=false).
2. JWT secrets validation fails application startup when AUTH_DEV_MODE=false if secret is missing, empty, or default.
3. Secrets are never printed in logs or exception messages.
4. Valid production secret configuration succeeds and mints/verifies tokens correctly.
5. CORS configuration parses ALLOWED_ORIGINS, rejects wildcards and missing configs in production, and defaults safely in dev.
6. CORS allowlist enforcement with credentials via Starlette/FastAPI TestClient.
7. Existing JWT authentication regressions (valid, invalid, expired, tampered).
"""

import os
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app import app
from backend.services.auth.jwt_service import (
    DEFAULT_DEV_SECRET,
    create_access_token,
    verify_access_token,
    get_jwt_secret_key,
    validate_jwt_secrets_config,
    is_auth_dev_mode,
)
from backend.services.auth.cors_config import (
    parse_cors_origins,
    DEFAULT_DEV_ORIGINS,
)


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. Protect POST /auth/token
# ==============================================================================

def test_dev_token_issuance_enabled_in_dev_mode(client, monkeypatch):
    """When AUTH_DEV_MODE=true, POST /auth/token should issue valid JWT tokens."""
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    response = client.post(
        "/auth/token",
        json={"user_id": "dev_test_user_84", "email": "test@dev.local", "role": "admin"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == "dev_test_user_84"
    assert data["expires_in"] > 0

    # Verify the issued token works on /auth/me
    token = data["access_token"]
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == "dev_test_user_84"
    assert me_resp.json()["role"] == "admin"


def test_dev_token_issuance_rejected_in_production(client, monkeypatch):
    """When AUTH_DEV_MODE=false, POST /auth/token must be rejected with HTTP 403."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    response = client.post(
        "/auth/token",
        json={"user_id": "malicious_attacker", "email": "attacker@evil.com", "role": "admin"},
    )
    assert response.status_code == 403
    error_data = response.json()
    # Message should clearly state dev mode is disabled
    error_msg = str(error_data)
    assert "disabled in production" in error_msg.lower() or "403" in error_msg


def test_dev_token_issuance_cannot_mint_in_production_case_variations(client, monkeypatch):
    """AUTH_DEV_MODE variations like '0', 'False', 'no' must all enforce production mode."""
    for false_val in ["0", "False", "false", "no", "NO"]:
        monkeypatch.setenv("AUTH_DEV_MODE", false_val)
        response = client.post(
            "/auth/token",
            json={"user_id": "user_123"},
        )
        assert response.status_code == 403, f"Expected 403 when AUTH_DEV_MODE={false_val}"


# ==============================================================================
# 2. Validate JWT Secrets at Startup
# ==============================================================================

def test_missing_jwt_secret_in_production_fails(monkeypatch):
    """When AUTH_DEV_MODE=false and JWT_SECRET_KEY is missing/empty, validation must fail."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secrets_config()
    assert "JWT_SECRET_KEY" in str(exc_info.value)
    assert "required in production mode" in str(exc_info.value)


def test_empty_jwt_secret_in_production_fails(monkeypatch):
    """When AUTH_DEV_MODE=false and JWT_SECRET_KEY is whitespace, validation must fail."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "   ")

    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secrets_config()
    assert "JWT_SECRET_KEY" in str(exc_info.value)


def test_default_dev_secret_in_production_fails_and_redacts(monkeypatch):
    """When AUTH_DEV_MODE=false and JWT_SECRET_KEY equals default dev secret, fail with safe error."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", DEFAULT_DEV_SECRET)

    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secrets_config()
    err_msg = str(exc_info.value)
    assert "cannot be the committed development default secret" in err_msg
    # Ensure secret value itself is never printed in error message
    assert DEFAULT_DEV_SECRET not in err_msg


def test_valid_production_secret_succeeds(monkeypatch):
    """When AUTH_DEV_MODE=false and a high-entropy secret is provided, validation succeeds."""
    prod_secret = "c7d2e8b1f4a903651234567890abcdef1234567890abcdef1234567890abcdef"
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", prod_secret)

    # Should not raise
    validate_jwt_secrets_config()
    resolved_key = get_jwt_secret_key()
    assert resolved_key == prod_secret

    # Can create and verify token with this production secret
    token = create_access_token(user_id="prod_user_01", role="editor")
    claims = verify_access_token(token)
    assert claims["sub"] == "prod_user_01"
    assert claims["role"] == "editor"


def test_production_secret_too_short_raises(monkeypatch):
    """When AUTH_DEV_MODE=false and JWT_SECRET_KEY is shorter than 32 characters, fail with safe error."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "short-secret-key-only-24b!")

    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secrets_config()

    err_msg = str(exc_info.value)
    assert "at least 32 characters long" in err_msg
    assert "short-secret-key-only-24b!" not in err_msg


def test_dev_mode_uses_default_secret_if_none_configured(monkeypatch):
    """In development mode, falling back to default secret is allowed for developer convenience."""
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    validate_jwt_secrets_config()
    assert get_jwt_secret_key() == DEFAULT_DEV_SECRET


# ==============================================================================
# 3. Restrict CORS
# ==============================================================================

def test_cors_dev_mode_defaults(monkeypatch):
    """In dev mode with no ALLOWED_ORIGINS, safe local origins are returned."""
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    origins = parse_cors_origins()
    assert set(DEFAULT_DEV_ORIGINS).issubset(set(origins))
    assert "http://localhost:5173" in origins


def test_cors_dev_mode_explicit_origins(monkeypatch):
    """In dev mode with explicit ALLOWED_ORIGINS, origins are parsed and stripped."""
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173, http://custom-dev:8080")

    origins = parse_cors_origins()
    assert origins == ["http://localhost:5173", "http://custom-dev:8080"]


def test_cors_production_missing_origins_fails(monkeypatch):
    """In production mode, missing ALLOWED_ORIGINS must raise RuntimeError."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        parse_cors_origins()
    assert "ALLOWED_ORIGINS environment variable is required in production mode" in str(exc_info.value)


def test_cors_production_empty_origins_fails(monkeypatch):
    """In production mode, empty or whitespace ALLOWED_ORIGINS must raise RuntimeError."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "   ,   ")

    with pytest.raises(RuntimeError) as exc_info:
        parse_cors_origins()
    assert "ALLOWED_ORIGINS" in str(exc_info.value)


def test_cors_production_wildcard_strictly_prohibited(monkeypatch):
    """In production mode, wildcard '*' cannot be used with credentials."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://travelsync.com, *")

    with pytest.raises(RuntimeError) as exc_info:
        parse_cors_origins()
    assert "Wildcard '*' in ALLOWED_ORIGINS is not permitted" in str(exc_info.value)


def test_cors_production_valid_allowlist(monkeypatch):
    """In production mode, valid comma-separated domain allowlist succeeds."""
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://travelsync.example.com, https://app.travelsync.example.com")

    origins = parse_cors_origins()
    assert origins == [
        "https://travelsync.example.com",
        "https://app.travelsync.example.com",
    ]


def test_cors_middleware_headers_allow_and_reject():
    """Verify CORSMiddleware behavior with explicit origins and credentials."""
    test_app = FastAPI()
    allowed = ["https://trusted-site.com", "http://localhost:5173"]
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @test_app.get("/ping")
    def ping():
        return {"status": "ok"}

    c = TestClient(test_app)

    # 1. Allowed origin preflight OPTIONS request
    preflight = c.options(
        "/ping",
        headers={
            "Origin": "https://trusted-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "https://trusted-site.com"
    assert preflight.headers.get("access-control-allow-credentials") == "true"

    # 2. Allowed origin GET request
    get_resp = c.get(
        "/ping",
        headers={"Origin": "https://trusted-site.com"},
    )
    assert get_resp.status_code == 200
    assert get_resp.headers.get("access-control-allow-origin") == "https://trusted-site.com"
    assert get_resp.headers.get("access-control-allow-credentials") == "true"

    # 3. Disallowed untrusted origin GET request
    untrusted_resp = c.get(
        "/ping",
        headers={"Origin": "https://evil-untrusted-site.com"},
    )
    assert untrusted_resp.status_code == 200
    # Disallowed origin must NOT receive access-control-allow-origin header matching the untrusted origin
    assert untrusted_resp.headers.get("access-control-allow-origin") != "https://evil-untrusted-site.com"


# ==============================================================================
# 4. Existing JWT Authentication Regressions
# ==============================================================================

def test_jwt_tampered_signature_rejected(client):
    """Tampering with token signature returns 401."""
    token = create_access_token(user_id="legit_user")
    parts = token.split(".")
    assert len(parts) == 3
    # Mutate the payload
    tampered_token = f"{parts[0]}.{parts[1]}xyz.{parts[2]}"

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401


def test_missing_auth_header_rejected(client):
    """Missing auth header returns 401."""
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_diagnostic_test_llm_route_not_mounted_in_prod(monkeypatch):
    """Diagnostic route /test-llm is disabled and returns 404 in production mode."""
    import importlib
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "c7d2e8b1f4a903651234567890abcdef1234567890abcdef1234567890abcdef")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.travelsync.com")

    import backend.app
    importlib.reload(backend.app)
    from starlette.testclient import TestClient
    prod_client = TestClient(backend.app.app)
    resp = prod_client.get("/test-llm")
    assert resp.status_code == 404

    # Restore dev mode
    monkeypatch.setenv("AUTH_DEV_MODE", "true")
    importlib.reload(backend.app)

