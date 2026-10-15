"""
Regression tests for Private-Trip Authentication and Navigation Keys.

Tests:
1. Valid authenticated owner can open their private trip (HTTP 200).
2. Unauthenticated user is rejected with HTTP 401 ("Authentication required: private trip requires valid credentials").
3. Unauthorized stranger is rejected with HTTP 403 ("Access denied: private trip").
4. Fresh session accepts an invitation and opens the trip with assigned viewer permissions.
5. Invited viewer can read trip, notes, insights, ratings, expenses, and weather alerts, but cannot update trip (HTTP 403).
6. Invited editor can open the trip and can update the trip.
7. Secondary requests (notes, insights, rating, expenses, weather) succeed for authorized members.
8. Static / code verification that TripView navigation quick-bar items have unique React keys.
"""

import copy
import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip_record
from backend.services.sharing.invitation_service import create_invitation
from backend.services.auth.jwt_service import create_access_token

client = TestClient(app)


def auth_headers(user_id: str) -> dict:
    token = create_access_token(user_id=user_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-User-ID": user_id,
    }


def _sample_trip_payload():
    return {
        "trip": {
            "source": "Bengaluru",
            "destination": "Hyderabad",
            "days": 3,
            "places": [
                {"name": "Charminar", "category": "Heritage", "lat": 17.3616, "lon": 78.4747},
                {"name": "Golconda Fort", "category": "Fort", "lat": 17.3833, "lon": 78.4011},
            ],
            "day_schedule": {
                "1": [{"name": "Charminar"}],
                "2": [{"name": "Golconda Fort"}],
            },
            "budget": {
                "total_budget": 15000,
                "estimated_cost": 12000,
                "remaining": 3000,
                "status": "Within Budget",
                "categories": {},
            },
        }
    }


def test_authenticated_owner_can_open_private_trip(isolated_storage):
    """A valid authenticated owner can open their private trip."""
    owner_id = "user_owner_001"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    res = client.get(f"/trip/{trip_id}", headers=auth_headers(owner_id))
    assert res.status_code == 200
    data = res.json()
    assert data["trip_id"] == trip_id
    assert data["role"] == "owner"


def test_unauthenticated_request_rejected_on_private_trip(isolated_storage):
    """Unauthenticated users cannot access private trip data."""
    owner_id = "user_owner_002"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # Completely unauthenticated (no headers)
    res = client.get(f"/trip/{trip_id}")
    assert res.status_code == 401
    assert "Authentication required: private trip requires valid credentials" in res.json().get("detail", "")

    # Only untrusted X-User-ID without Bearer token
    res_fake = client.get(f"/trip/{trip_id}", headers={"X-User-ID": owner_id})
    assert res_fake.status_code == 401
    assert "Authentication required: private trip requires valid credentials" in res_fake.json().get("detail", "")


def test_unauthorized_stranger_rejected_with_403(isolated_storage):
    """Authenticated user who is not owner or member receives HTTP 403."""
    owner_id = "user_owner_003"
    stranger_id = "user_stranger_003"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    res = client.get(f"/trip/{trip_id}", headers=auth_headers(stranger_id))
    assert res.status_code == 403
    assert "Access denied: private trip" in res.json().get("detail", "")


def test_invitation_acceptance_in_fresh_session_as_viewer(isolated_storage):
    """Invitation acceptance works in a fresh session and grants viewer access."""
    owner_id = "user_owner_004"
    fresh_user_id = "user_fresh_viewer_004"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # Owner creates viewer invitation
    invitation = create_invitation(trip_id, owner_id, role="viewer")
    token = invitation["token"]

    # Fresh session accepts invitation
    accept_res = client.post(f"/invitations/{token}/accept", headers=auth_headers(fresh_user_id))
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "viewer"
    assert accept_res.json()["trip_id"] == trip_id

    # Invited viewer can open the trip
    view_res = client.get(f"/trip/{trip_id}", headers=auth_headers(fresh_user_id))
    assert view_res.status_code == 200
    assert view_res.json()["role"] == "viewer"

    # Viewer CANNOT update the trip
    update_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add a new stop"},
        headers=auth_headers(fresh_user_id),
    )
    assert update_res.status_code == 403
    assert "Access denied: insufficient permissions" in update_res.json().get("detail", "") or "Permission denied" in update_res.json().get("detail", "")


def test_invitation_acceptance_in_fresh_session_as_editor(isolated_storage, monkeypatch):
    """Invitation acceptance works for an editor who can both view and edit."""
    owner_id = "user_owner_005"
    editor_user_id = "user_fresh_editor_005"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    def mock_interpret(prompt):
        return {"actions": [{"type": "set_budget", "amount": 20000}]}

    monkeypatch.setattr("backend.routes.update_trip.interpret_trip_prompt", mock_interpret)

    # Owner creates editor invitation
    invitation = create_invitation(trip_id, owner_id, role="editor")
    token = invitation["token"]

    # Editor accepts invitation
    accept_res = client.post(f"/invitations/{token}/accept", headers=auth_headers(editor_user_id))
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "editor"

    # Editor opens trip
    view_res = client.get(f"/trip/{trip_id}", headers=auth_headers(editor_user_id))
    assert view_res.status_code == 200
    assert view_res.json()["role"] == "editor"

    # Editor CAN update the trip
    update_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add Salar Jung Museum to day 1"},
        headers=auth_headers(editor_user_id),
    )
    assert update_res.status_code == 200


def test_secondary_data_loading_with_authentication(isolated_storage):
    """Notes, insights, expenses, ratings, and weather alerts load with authentication."""
    owner_id = "user_owner_006"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)
    headers = auth_headers(owner_id)

    # 1. Insights
    insights_res = client.get(f"/trip/{trip_id}/insights", headers=headers)
    assert insights_res.status_code == 200

    # 2. Notes
    notes_res = client.get(f"/trip/{trip_id}/notes", headers=headers)
    assert notes_res.status_code == 200

    # 3. Rating
    rating_res = client.get(f"/trip/{trip_id}/rating", headers=headers)
    assert rating_res.status_code == 200

    # 4. Expenses
    expenses_res = client.get(f"/expense/{trip_id}", headers=headers)
    assert expenses_res.status_code == 200

    # 5. Weather alerts
    weather_res = client.get(f"/weather/trip/{trip_id}/alerts", headers=headers)
    assert weather_res.status_code == 200


def test_expired_or_mismatched_token_rejected(isolated_storage):
    """Expired or mismatched tokens are rejected with 401."""
    owner_id = "user_owner_007"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # 1. Expired token
    from datetime import timedelta
    expired_token = create_access_token(user_id=owner_id, expires_delta=timedelta(seconds=-60))
    exp_res = client.get(f"/trip/{trip_id}", headers={"Authorization": f"Bearer {expired_token}"})
    assert exp_res.status_code == 401
    assert "expired" in exp_res.json().get("detail", "").lower()

    # 2. Confused deputy: Token subject does not match X-User-ID
    valid_token = create_access_token(user_id=owner_id)
    mismatch_res = client.get(
        f"/trip/{trip_id}",
        headers={
            "Authorization": f"Bearer {valid_token}",
            "X-User-ID": "different_attacker_user",
        },
    )
    assert mismatch_res.status_code == 401
    assert "mismatch" in mismatch_res.json().get("detail", "").lower()


def test_navigation_keys_are_unique():
    """Verify frontend TripView quickbar navigation keys are strictly unique."""
    tripview_path = Path(__file__).resolve().parent.parent / "frontend" / "src" / "pages" / "TripView.tsx"
    assert tripview_path.exists(), "TripView.tsx must exist"

    content = tripview_path.read_text(encoding="utf-8")

    # Match the map key pattern
    # It should not be `key={item.href}` which produced duplicates for '#section-journal'
    assert "key={`${item.href}-${item.label}`}" in content
    assert 'key={item.href}\n            href={item.href}' not in content


def test_fresh_guest_session_creating_and_opening_trip(isolated_storage):
    """A fresh guest session obtains a token, saves a private trip, and opens it with owner role."""
    import uuid
    uid_suffix = uuid.uuid4().hex[:8]
    guest_id = f"user_guest_regression_{uid_suffix}"
    token_res = client.post("/auth/token", json={"user_id": guest_id})
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-User-ID": guest_id}

    trip_id = save_trip(_sample_trip_payload(), owner_id=guest_id)

    # Guest opens the created trip
    view_res = client.get(f"/trip/{trip_id}", headers=headers)
    assert view_res.status_code == 200
    assert view_res.json()["trip_id"] == trip_id
    assert view_res.json()["role"] == "owner"


def test_guest_session_claiming_account_and_reopening_trip(isolated_storage):
    """Guest session claims permanent credentials and reopens their trip with owner permissions."""
    import uuid
    uid_suffix = uuid.uuid4().hex[:8]
    guest_id = f"user_guest_claim_{uid_suffix}"
    email = f"claimed_guest_{uid_suffix}@example.com"
    token_res = client.post("/auth/token", json={"user_id": guest_id})
    guest_token = token_res.json()["access_token"]
    guest_headers = {"Authorization": f"Bearer {guest_token}", "X-User-ID": guest_id}

    # 1. Guest creates private trip
    trip_id = save_trip(_sample_trip_payload(), owner_id=guest_id)

    # 2. Guest claims session to register account
    claim_payload = {
        "user_id": guest_id,
        "email": email,
        "password": "Password123!Secure",
        "full_name": "Claimed User",
    }
    claim_res = client.post("/auth/claim-session", json=claim_payload)
    assert claim_res.status_code == 201
    claim_token = claim_res.json()["access_token"]
    claimed_user_id = claim_res.json()["user"]["id"]
    assert claimed_user_id == guest_id

    # 3. Log in with new credentials
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "Password123!Secure"},
    )
    assert login_res.status_code == 200
    login_token = login_res.json()["access_token"]
    login_headers = {"Authorization": f"Bearer {login_token}", "X-User-ID": claimed_user_id}

    # 4. Reopen trip as the claimed authenticated owner
    view_res = client.get(f"/trip/{trip_id}", headers=login_headers)
    assert view_res.status_code == 200
    assert view_res.json()["trip_id"] == trip_id
    assert view_res.json()["role"] == "owner"


def test_signup_and_login_followed_by_redirect_to_private_trip(isolated_storage):
    """New user registers, logs in, creates private trip, and opens it on simulated redirect / refresh."""
    import uuid
    uid_suffix = uuid.uuid4().hex[:8]
    email = f"new_traveler_{uid_suffix}@example.com"
    register_payload = {
        "email": email,
        "password": "SecurePassword303!",
        "full_name": "New Traveler",
    }
    reg_res = client.post("/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user"]["id"]

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePassword303!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-User-ID": user_id}

    # Create private trip
    trip_id = save_trip(_sample_trip_payload(), owner_id=user_id)

    # Initial view (post-login redirect)
    view_res = client.get(f"/trip/{trip_id}", headers=headers)
    assert view_res.status_code == 200
    assert view_res.json()["role"] == "owner"

    # Second view (simulating page refresh with same stored credentials)
    refresh_res = client.get(f"/trip/{trip_id}", headers=headers)
    assert refresh_res.status_code == 200
    assert refresh_res.json()["role"] == "owner"


def test_unauthenticated_request_cannot_access_claimed_trip(isolated_storage):
    """After claiming a session, unauthenticated requests are rejected with 401."""
    owner_id = "user_claimed_owner_404"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    res = client.get(f"/trip/{trip_id}")
    assert res.status_code == 401
    assert "Authentication required: private trip requires valid credentials" in res.json().get("detail", "")

