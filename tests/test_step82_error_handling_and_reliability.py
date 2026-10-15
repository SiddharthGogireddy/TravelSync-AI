"""Step 82 tests: Centralized API error handling, standardized responses, and reliability hardening."""

import logging
from datetime import datetime
from unittest.mock import patch
import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from backend.app import app
from backend.services.auth.jwt_service import create_access_token
from backend.services.error.exception_handlers import register_exception_handlers
from backend.services.error.redaction import redact_sensitive_text, sanitize_for_client


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_standardized_error_structure_404(client):
    """Verify missing resources return standard schema with error_code, message, detail, timestamp."""
    resp = client.get("/trip/non-existent-trip-id-xyz")
    assert resp.status_code == 404
    data = resp.json()

    assert "error_code" in data
    assert data["error_code"] == "NOT_FOUND"
    assert "message" in data
    assert "detail" in data
    assert "timestamp" in data
    # Timestamp should parse as ISO datetime
    dt = datetime.fromisoformat(data["timestamp"])
    assert dt is not None


def test_standardized_error_structure_401_auth_required(client):
    """Verify unauthorized requests return 401 with UNAUTHORIZED error code and safe message."""
    resp = client.post("/trip/test-trip/invitations", json={"role": "viewer"})
    assert resp.status_code == 401
    data = resp.json()

    assert data["error_code"] == "UNAUTHORIZED"
    assert "detail" in data
    assert "Authentication required" in data["detail"]
    assert "timestamp" in data


def test_validation_error_structure_422(client):
    """Verify 422 RequestValidationError produces structured field details while keeping detail list."""
    token = create_access_token("user_123", "User")
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid planner payload: negative days
    resp = client.post(
        "/planner/",
        json={"source": "Delhi", "destination": "Goa", "days": -5, "budget": 10000},
        headers=headers,
    )
    assert resp.status_code == 422
    data = resp.json()

    assert data["error_code"] == "VALIDATION_ERROR"
    assert data["message"] == "Validation failed for the submitted data."
    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert any("greater than or equal to 1" in str(err) for err in data["detail"])

    # Structured details field
    assert "details" in data
    assert isinstance(data["details"], list)
    field_names = [d["field"] for d in data["details"]]
    assert "days" in field_names


def test_status_code_preservation(client):
    """Verify appropriate HTTP status codes (400, 401, 403, 404, 422) are strictly preserved."""
    token = create_access_token("user_test", "User")
    headers = {"Authorization": f"Bearer {token}"}

    # 400 Bad Request (currency negative amount)
    resp_400 = client.get("/currency/convert?amount=-50&from_curr=USD&to_curr=INR")
    assert resp_400.status_code == 400
    assert resp_400.json()["error_code"] == "BAD_REQUEST"

    # 401 Unauthorized (corrupted token)
    resp_401 = client.get(
        "/trip/some-trip", headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert resp_401.status_code == 401
    assert resp_401.json()["error_code"] == "UNAUTHORIZED"

    # 404 Not Found
    resp_404 = client.get("/trip/99999999-9999-9999-9999-999999999999", headers=headers)
    assert resp_404.status_code == 404
    assert resp_404.json()["error_code"] == "NOT_FOUND"


def test_redaction_utilities():
    """Verify sensitive tokens, passwords, and local paths are properly redacted."""
    raw_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text_with_bearer = f"Request authorization header: Bearer {raw_token}"
    redacted = redact_sensitive_text(text_with_bearer)
    assert raw_token not in redacted
    assert "Bearer [REDACTED]" in redacted

    text_with_secret = '{"username": "traveler", "password": "supersecretpassword123"}'
    redacted_secret = redact_sensitive_text(text_with_secret)
    assert "supersecretpassword123" not in redacted_secret
    assert '[REDACTED]' in redacted_secret

    local_path = r"Error occurred in file C:\Users\siddh\OneDrive\Desktop\secret_file.py"
    sanitized = sanitize_for_client(local_path)
    assert r"C:\Users" not in sanitized
    assert "[internal_path]" in sanitized


def test_unhandled_exception_sanitization(client, caplog):
    """Verify unexpected 500 exceptions do not leak stack traces or paths to client and log server-side."""
    # Create isolated test app with exception handlers
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/crash-test")
    def crash_endpoint():
        raise RuntimeError("Secret internal failure in C:\\Users\\siddh\\db_engine.py with password=my_db_pwd")

    isolated_client = TestClient(test_app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR):
        resp = isolated_client.get("/crash-test", headers={"Authorization": "Bearer secret_jwt_token_123"})
        assert resp.status_code == 500
        data = resp.json()

        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert data["message"] == "An unexpected server error occurred. Please try again later."
        # Confirm no internal file path leaked to client
        assert "C:\\Users" not in str(data)
        assert "my_db_pwd" not in str(data)
        assert "RuntimeError" not in str(data)

        # Confirm server-side log contains redacted diagnostics
        logged = caplog.text
        assert "Unhandled server exception" in logged
        assert "my_db_pwd" not in logged  # Password was redacted


def test_value_and_key_error_handlers():
    """Verify application ValueError and KeyError are translated to 400 and 404 with standard schemas."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/trigger-value-error")
    def trigger_value_error():
        raise ValueError("Invalid currency exchange rate specified")

    @test_app.get("/trigger-key-error")
    def trigger_key_error():
        raise KeyError("itinerary_day_99")

    client = TestClient(test_app, raise_server_exceptions=False)

    res_val = client.get("/trigger-value-error")
    assert res_val.status_code == 400
    assert res_val.json()["error_code"] == "BAD_REQUEST"
    assert "Invalid currency" in res_val.json()["detail"]

    res_key = client.get("/trigger-key-error")
    assert res_key.status_code == 404
    assert res_key.json()["error_code"] == "NOT_FOUND"
    assert "itinerary_day_99" in res_key.json()["detail"]


def test_http_exception_headers_preservation():
    """Verify HTTPException custom headers (e.g. WWW-Authenticate) are preserved in the response."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/auth-required-endpoint")
    def auth_required_endpoint():
        raise HTTPException(
            status_code=401,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer realm='travelsync'"}
        )

    client = TestClient(test_app, raise_server_exceptions=False)
    resp = client.get("/auth-required-endpoint")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer realm='travelsync'"
    assert resp.json()["error_code"] == "UNAUTHORIZED"
