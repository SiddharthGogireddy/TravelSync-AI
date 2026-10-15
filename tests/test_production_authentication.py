import os
import pytest
from starlette.testclient import TestClient

from backend.app import app
from backend.services.auth.jwt_service import (
    create_access_token,
    verify_access_token,
    DEFAULT_DEV_SECRET,
)
from backend.services.auth.user_store import (
    hash_password,
    verify_password,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_user_db(tmp_path, monkeypatch):
    """Ensure each test runs with an isolated users SQLite database."""
    test_db = tmp_path / "test_users.db"
    monkeypatch.setenv("TRAVELSYNC_USERS_DB", str(test_db))
    return test_db


def test_password_hashing_and_verification():
    """Verify PBKDF2 hashing with salt and constant-time verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed.startswith("pbkdf2_sha256:600000:")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "invalid_hash_format") is False


def test_register_new_user_success():
    """Verify standard user registration returns 201 with access token."""
    payload = {
        "email": "traveler@example.com",
        "password": "SecurePassword2026!",
        "full_name": "Alice Traveler",
    }
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "traveler@example.com"
    assert data["user"]["full_name"] == "Alice Traveler"
    assert data["user"]["role"] == "user"
    assert data["user"]["id"].startswith("user_")

    # Verify token payload
    claims = verify_access_token(data["access_token"])
    assert claims["sub"] == data["user"]["id"]
    assert claims["email"] == "traveler@example.com"


def test_register_duplicate_email_rejected():
    """Registering with an already existing email returns 400 Bad Request."""
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword2026!",
        "full_name": "Bob",
    }
    resp1 = client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_register_short_password_rejected():
    """Password with less than 8 characters is rejected."""
    payload = {
        "email": "short@example.com",
        "password": "short",
    }
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code in (400, 422)


def test_login_success():
    """Registered user can log in with email and password."""
    reg_payload = {
        "email": "login_test@example.com",
        "password": "MySecretPassword2026!",
        "full_name": "Charlie",
    }
    reg_resp = client.post("/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["user"]["id"]

    login_payload = {
        "email": "login_test@example.com",
        "password": "MySecretPassword2026!",
    }
    login_resp = client.post("/auth/login", json=login_payload)
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()

    assert "access_token" in login_data
    assert login_data["user"]["id"] == user_id
    assert login_data["user"]["email"] == "login_test@example.com"

    # Test /auth/me with the received token
    me_resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user_id"] == user_id
    assert me_data["email"] == "login_test@example.com"
    assert me_data["full_name"] == "Charlie"


def test_login_invalid_password_rejected():
    """Login with wrong password returns 401 Unauthorized."""
    reg_payload = {
        "email": "wrongpwd@example.com",
        "password": "CorrectPassword2026!",
    }
    client.post("/auth/register", json=reg_payload)

    login_resp = client.post(
        "/auth/login",
        json={"email": "wrongpwd@example.com", "password": "WrongPassword!"},
    )
    assert login_resp.status_code == 401
    assert "Invalid email or password" in login_resp.json()["detail"]


def test_login_nonexistent_email_rejected():
    """Login with non-registered email returns 401 Unauthorized."""
    login_resp = client.post(
        "/auth/login",
        json={"email": "doesnotexist@example.com", "password": "AnyPassword123!"},
    )
    assert login_resp.status_code == 401


def test_claim_session_preserves_existing_user_id():
    """
    Session claiming enables an existing guest user to register with email/password
    while retaining their exact existing user_id and trip ownership.
    """
    existing_guest_id = "user_c8b0c80f_legacy"
    claim_payload = {
        "user_id": existing_guest_id,
        "email": "claimed_guest@example.com",
        "password": "PasswordForGuest2026!",
        "full_name": "Guest Converted",
    }
    claim_resp = client.post("/auth/claim-session", json=claim_payload)
    assert claim_resp.status_code == 201, claim_resp.text
    claim_data = claim_resp.json()

    # The user_id must match the claimed legacy user_id
    assert claim_data["user"]["id"] == existing_guest_id
    assert claim_data["user"]["email"] == "claimed_guest@example.com"

    claims = verify_access_token(claim_data["access_token"])
    assert claims["sub"] == existing_guest_id

    # The user can now log in normally using their credentials
    login_resp = client.post(
        "/auth/login",
        json={
            "email": "claimed_guest@example.com",
            "password": "PasswordForGuest2026!",
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["id"] == existing_guest_id


def test_claim_session_duplicate_rejected():
    """Attempting to claim an already registered user ID returns 400."""
    payload = {
        "user_id": "user_already_claimed",
        "email": "first@example.com",
        "password": "Password2026!",
    }
    resp1 = client.post("/auth/claim-session", json=payload)
    assert resp1.status_code == 201

    dup_payload = {
        "user_id": "user_already_claimed",
        "email": "second@example.com",
        "password": "Password2026!",
    }
    resp2 = client.post("/auth/claim-session", json=dup_payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_auth_works_in_production_mode(monkeypatch):
    """
    Critical production-readiness check:
    When AUTH_DEV_MODE=false, /auth/token is rejected (403),
    but /auth/register and /auth/login work seamlessly!
    """
    prod_secret = "c7d2e8b1f4a903651234567890abcdef1234567890abcdef1234567890abcdef"
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", prod_secret)

    # 1. Dev token endpoint is forbidden in production
    dev_resp = client.post("/auth/token", json={"user_id": "some_user"})
    assert dev_resp.status_code == 403

    # 2. Production registration succeeds
    reg_resp = client.post(
        "/auth/register",
        json={
            "email": "prod_user@company.com",
            "password": "ProductionPassword2026!",
            "full_name": "Prod User",
        },
    )
    assert reg_resp.status_code == 201
    prod_token = reg_resp.json()["access_token"]
    prod_user_id = reg_resp.json()["user"]["id"]

    # 3. Production login succeeds
    login_resp = client.post(
        "/auth/login",
        json={
            "email": "prod_user@company.com",
            "password": "ProductionPassword2026!",
        },
    )
    assert login_resp.status_code == 200

    # 4. Authenticated request with production token succeeds
    me_resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {prod_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == prod_user_id
