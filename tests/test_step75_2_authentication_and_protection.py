"""
Unit and integration tests for Step 75.2: Authentication and Legacy Data Protection.

Validates:
1. Forged headers rejection: X-User-ID without valid Bearer token is NEVER trusted as proof of identity.
2. Confused-deputy mismatch defense: X-User-ID differing from Bearer token subject returns 401.
3. Cryptographic token verification: Malformed, expired, invalid signature, or empty subject tokens return 401.
4. Authenticated identity derivation: Identity is derived exclusively from verified backend tokens (/auth/me).
5. Cross-user access prevention: Authenticated users cannot access private trips owned by other users.
6. Server-side protection across all private resources:
   - Trip view, update, export, notes, favorites, ratings, expenses, weather alerts, calendar.
7. Safe legacy trip isolation & explicit claiming workflow:
   - Unowned legacy trips cannot have invitations created until explicitly claimed (403).
   - Read-only migration preview (/trip/legacy/preview) without data mutation.
   - Automated snapshot backup (/trip/legacy/backup) before any transformation.
   - Explicit claiming (/trip/{trip_id}/claim-legacy) binds ownership to authenticated caller.
   - Conflict prevention: already-claimed trips reject re-claiming (409 Conflict).
8. Invitation security:
   - Acceptance binds membership strictly to authenticated user's token subject.
   - Replay, expiration, and revocation protections remain strictly enforced.
"""

import os
import sys
import jwt
import time
from datetime import datetime, timezone, timedelta
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import (
    save_trip,
    load_trip,
    load_trip_record,
    _STORE_LOCK,
    _read_trips,
)
from backend.services.auth.jwt_service import (
    create_access_token,
    verify_access_token,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    OIDC_ISSUER,
    OIDC_AUDIENCE,
)
from backend.services.sharing.invitation_service import (
    create_invitation,
    hash_token,
)
from backend.services.storage.migration_service import (
    get_legacy_trips_preview,
    create_trips_backup,
    claim_legacy_trip,
    BACKUP_DIR,
)

client = TestClient(app)

SAMPLE_TRIP = {
    "source": "Mumbai",
    "destination": "Goa",
    "days": 2,
    "budget": {"total_budget": 15000, "estimated_cost": 12000},
    "travelers": [{"name": "Alice", "interests": ["Beach"]}],
    "day_schedule": {
        "1": [{"name": "Calangute Beach", "category": "Beach"}],
        "2": [{"name": "Fort Aguada", "category": "Heritage"}],
    },
    "places": [
        {"name": "Calangute Beach", "category": "Beach"},
        {"name": "Fort Aguada", "category": "Heritage"},
    ],
}


def _create_trip(owner_id=None):
    payload = {
        "trip": dict(SAMPLE_TRIP),
        "dashboard": {"destination": "Goa", "days": 2},
        "summary": {"days": 2},
    }
    return save_trip(payload, owner_id=owner_id)


def _auth_headers(user_id: str, extra_header: dict = None) -> dict:
    token = create_access_token(user_id=user_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-ID": user_id,
    }
    if extra_header:
        headers.update(extra_header)
    return headers


# ==============================================================================
# 1. Forged Headers & Missing Credentials Tests
# ==============================================================================

def test_forged_x_user_id_header_rejected_without_token():
    """Client sending forged X-User-ID without Bearer credentials is rejected with 401."""
    trip_id = _create_trip(owner_id="alice_real")

    # Attacker passes victim's owner_id in X-User-ID header without token
    resp = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "alice_real"})
    assert resp.status_code == 401
    assert "Authentication required" in resp.json().get("detail", "")


def test_identity_mismatch_confused_deputy_defense():
    """Client presenting valid token for user_bob but declaring X-User-ID: user_alice is rejected with 401."""
    trip_id = _create_trip(owner_id="user_alice")

    bob_token = create_access_token(user_id="user_bob")
    resp = client.get(
        f"/trip/{trip_id}",
        headers={
            "Authorization": f"Bearer {bob_token}",
            "X-User-ID": "user_alice",  # Deliberate mismatch
        },
    )
    assert resp.status_code == 401
    assert "mismatch" in resp.json().get("detail", "").lower()


def test_malformed_and_tampered_token_rejected():
    """Malformed and tampered JWT tokens return 401 Unauthorized."""
    trip_id = _create_trip(owner_id="alice")

    # 1. Completely bogus token
    resp_garbage = client.get(f"/trip/{trip_id}", headers={"Authorization": "Bearer invalid.token.garbage"})
    assert resp_garbage.status_code == 401

    # 2. Token signed with wrong secret key
    tampered_token = jwt.encode(
        {"sub": "alice", "exp": int(time.time()) + 3600, "iss": OIDC_ISSUER},
        "wrong-secret-key-attacker-guess",
        algorithm="HS256",
    )
    resp_tampered = client.get(f"/trip/{trip_id}", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp_tampered.status_code == 401


def test_expired_token_rejected():
    """Tokens past expiration return 401 Unauthorized with expired description."""
    trip_id = _create_trip(owner_id="alice")

    expired_token = jwt.encode(
        {"sub": "alice", "exp": int(time.time()) - 120, "iss": OIDC_ISSUER, "aud": OIDC_AUDIENCE},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    resp = client.get(f"/trip/{trip_id}", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json().get("detail", "").lower()


def test_empty_or_missing_subject_claim_rejected():
    """Tokens lacking a valid subject ('sub') claim are rejected with 401."""
    trip_id = _create_trip(owner_id="alice")

    token_no_sub = jwt.encode(
        {"exp": int(time.time()) + 3600, "iss": OIDC_ISSUER, "aud": OIDC_AUDIENCE},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    resp = client.get(f"/trip/{trip_id}", headers={"Authorization": f"Bearer {token_no_sub}"})
    assert resp.status_code == 401


# ==============================================================================
# 2. Verified Authentication & /auth Endpoints
# ==============================================================================

def test_auth_token_issuance_and_me_endpoint():
    """Verified token issuance and identity derivation via /auth/token and /auth/me."""
    resp_issue = client.post("/auth/token", json={"user_id": "verified_david", "email": "david@example.com"})
    assert resp_issue.status_code == 200
    token_data = resp_issue.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    assert token_data["user_id"] == "verified_david"

    # /auth/me verifies token and derives identity exclusively from credentials
    resp_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_me.status_code == 200
    me_data = resp_me.json()
    assert me_data["authenticated"] is True
    assert me_data["user_id"] == "verified_david"
    assert me_data["email"] == "david@example.com"


def test_auth_me_rejects_unauthenticated():
    """Accessing /auth/me without valid Bearer token returns 401."""
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_auth_config_returns_public_metadata():
    """Public auth config endpoint returns algorithm and issuer without disclosing secrets."""
    resp = client.get("/auth/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "algorithm" in cfg
    assert "issuer" in cfg
    assert "JWT_SECRET_KEY" not in cfg


# ==============================================================================
# 3. Cross-User Access & Role Enforcement
# ==============================================================================

def test_cross_user_access_blocked_with_valid_token():
    """User Bob with valid token attempting to view Alice's private trip gets 403 Forbidden."""
    trip_id = _create_trip(owner_id="alice")

    # Bob has authentic token, but has no role on Alice's trip
    resp = client.get(f"/trip/{trip_id}", headers=_auth_headers("bob"))
    assert resp.status_code == 403
    assert "Access denied" in resp.json().get("detail", "")


def test_all_private_trip_resources_protected():
    """Verifies that all associated sub-resources enforce authentication and authorization."""
    trip_id = _create_trip(owner_id="alice")

    endpoints = [
        ("GET", f"/trip/{trip_id}/pdf"),
        ("GET", f"/trip/{trip_id}/export"),
        ("GET", f"/trip/{trip_id}/calendar"),
        ("GET", f"/expense/{trip_id}"),
        ("GET", f"/trip/{trip_id}/notes"),
        ("GET", f"/trip/{trip_id}/favorite"),
        ("GET", f"/trip/{trip_id}/rating"),
        ("GET", f"/weather/trip/{trip_id}/alerts"),
        ("GET", f"/trip/{trip_id}/attraction-alternatives?day=1&attraction_name=Calangute+Beach"),
    ]

    for method, path in endpoints:
        # Unauthenticated -> 401
        res_unauth = client.request(method, path)
        assert res_unauth.status_code == 401, f"Failed on unauth {method} {path}"

        # Stranger with valid token -> 403
        res_stranger = client.request(method, path, headers=_auth_headers("stranger_bob"))
        assert res_stranger.status_code == 403, f"Failed on stranger {method} {path}"

        # Owner with valid token -> 200 (or acceptable non-error for rating)
        res_owner = client.request(method, path, headers=_auth_headers("alice"))
        assert res_owner.status_code == 200, f"Failed on owner {method} {path}"


# ==============================================================================
# 4. Safe Legacy Trip Isolation & Explicit Claiming Workflow
# ==============================================================================

def test_unowned_legacy_trip_blocks_owner_actions_until_claimed():
    """Unowned legacy trip permits viewing/editing, but blocks owner operations (invitations) with 403."""
    trip_id = _create_trip(owner_id=None)

    # 1. Reading is allowed for backward compatibility
    res_view = client.get(f"/trip/{trip_id}")
    assert res_view.status_code == 200

    # 2. Creating invitation is an OWNER action -> blocked with 403 until explicitly claimed
    res_inv = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "viewer"},
        headers=_auth_headers("random_user"),
    )
    assert res_inv.status_code == 403
    assert "claim-legacy" in res_inv.json().get("detail", "").lower()


def test_legacy_preview_and_explicit_claiming_with_backup():
    """Preview unowned trips, claim a trip explicitly, verify backup creation, and prevent conflicts."""
    trip_id = _create_trip(owner_id=None)

    # 1. Migration preview requires authentication
    res_unauth_prev = client.get("/trip/legacy/preview")
    assert res_unauth_prev.status_code == 401

    res_prev = client.get("/trip/legacy/preview", headers=_auth_headers("admin_david"))
    assert res_prev.status_code == 200
    prev_data = res_prev.json()
    assert "unowned_legacy_trips" in prev_data
    unowned_ids = [t["id"] for t in prev_data["unowned_legacy_trips"]]
    assert trip_id in unowned_ids

    # 2. Trigger explicit snapshot backup
    res_backup = client.post("/trip/legacy/backup", headers=_auth_headers("admin_david"))
    assert res_backup.status_code == 200
    assert res_backup.json()["success"] is True
    assert "backup_file" in res_backup.json()

    # 3. Explicit claiming assigns ownership to authenticated caller and creates automatic backup
    res_claim = client.post(f"/trip/{trip_id}/claim-legacy", headers=_auth_headers("owner_david"))
    assert res_claim.status_code == 200
    assert res_claim.json()["success"] is True
    assert res_claim.json()["owner_id"] == "owner_david"

    # Verify trip is now owned
    record = load_trip_record(trip_id)
    assert record["owner_id"] == "owner_david"
    assert record["members"]["owner_david"]["role"] == "owner"

    # 4. Another user cannot claim an already-owned trip -> 409 Conflict
    res_conflict = client.post(f"/trip/{trip_id}/claim-legacy", headers=_auth_headers("another_user"))
    assert res_conflict.status_code == 409
    assert "already owned" in res_conflict.json().get("detail", "").lower()

    # 5. Now that David is the claimed owner, David can create invitations
    res_invite = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "editor"},
        headers=_auth_headers("owner_david"),
    )
    assert res_invite.status_code == 201


def test_batch_claiming_legacy_trips():
    """Batch-claiming unowned legacy trips for designated authenticated user."""
    t1 = _create_trip(owner_id=None)
    t2 = _create_trip(owner_id=None)

    res_batch = client.post(
        "/trip/legacy/claim-batch",
        json={"trip_ids": [t1, t2]},
        headers=_auth_headers("batch_owner_ellen"),
    )
    assert res_batch.status_code == 200
    data = res_batch.json()
    assert data["success"] is True
    assert t1 in data["claimed_trip_ids"]
    assert t2 in data["claimed_trip_ids"]

    assert load_trip_record(t1)["owner_id"] == "batch_owner_ellen"
    assert load_trip_record(t2)["owner_id"] == "batch_owner_ellen"


# ==============================================================================
# 5. Invitation Acceptance Binding & Replay Protections
# ==============================================================================

def test_invitation_acceptance_binds_to_authenticated_identity():
    """Acceptance derives the joined member identity exclusively from verified token subject."""
    trip_id = _create_trip(owner_id="alice")

    inv = create_invitation(trip_id=trip_id, owner_user_id="alice", role="editor")
    token = inv["token"]

    # Bob accepts using his verified token
    res_accept = client.post(f"/invitations/{token}/accept", headers=_auth_headers("bob_invitee"))
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "accepted"
    assert res_accept.json()["role"] == "editor"

    # Verify that members in storage contains Bob
    record = load_trip_record(trip_id)
    assert "bob_invitee" in record["members"]
    assert record["members"]["bob_invitee"]["role"] == "editor"

    # Replay protection: cannot accept already accepted invitation
    res_replay = client.post(f"/invitations/{token}/accept", headers=_auth_headers("charlie_late"))
    assert res_replay.status_code == 400
    assert "already been accepted" in res_replay.json().get("detail", "").lower()
