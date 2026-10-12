"""
Unit and integration tests for Step 75: Shared Trips and Invitations Foundation.
Validates:
- Private trip default isolation (strangers/unauthenticated blocked with 403)
- Unguessable invitation tokens with SHA-256 hash storage (raw token never in DB)
- Owner permissions: create invites, view history, revoke
- Editor permissions: can view and modify activities/notes, cannot invite
- Viewer permissions: can view trip/weather/calendar, write/edit blocked with 403
- Expiration: expired invitations cannot be accepted
- Revocation: revoked invitations cannot be accepted
- History isolation: private trips hidden from unrelated users
- Concurrency lock protection on trip storage
- Backward compatibility: unowned legacy trips remain accessible
"""

import copy
import hashlib
import os
import sys
import threading
from datetime import datetime, timezone, timedelta
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import (
    save_trip,
    load_trip,
    load_trip_record,
    load_all_trips,
    update_trip_sharing,
    _read_trips,
)
from backend.services.sharing.invitation_service import (
    hash_token,
    create_invitation,
    list_trip_invitations,
    revoke_invitation,
    get_invitation_preview,
    accept_invitation,
    decline_invitation,
)

client = TestClient(app)


def _sample_trip_payload(destination="Goa", source="Mumbai"):
    return {
        "trip": {
            "source": source,
            "destination": destination,
            "days": 2,
            "places": [
                {"name": "Baga Beach", "category": "Beach", "lat": 15.55, "lon": 73.75},
                {"name": "Fort Aguada", "category": "Historic", "lat": 15.49, "lon": 73.77},
            ],
            "day_schedule": {
                "1": [{"name": "Baga Beach", "category": "Beach", "lat": 15.55, "lon": 73.75}],
                "2": [{"name": "Fort Aguada", "category": "Historic", "lat": 15.49, "lon": 73.77}],
            },
            "hotels": [{"name": "Taj Holiday Village", "distance_km": 1.2}],
            "travelers": [{"name": "Alice", "interests": ["beach"], "budget": "medium", "pace": "relaxed"}],
            "budget": {
                "total_budget": 20000,
                "estimated_cost": 15000,
                "remaining": 5000,
                "status": "Within Budget",
                "categories": {"hotel": 8000, "food": 4000, "activities": 3000},
            },
        },
        "dashboard": {},
        "summary": {},
    }


# =====================================================================
# 1. Private Trip Isolation Tests
# =====================================================================

def test_private_trip_isolation_blocks_strangers():
    """Private trips cannot be accessed by unauthenticated users or strangers without membership."""
    owner_id = "user_owner_alpha"
    stranger_id = "user_stranger_beta"
    payload = _sample_trip_payload()

    trip_id = save_trip(payload, owner_id=owner_id)

    # 1. Unauthenticated request (no X-User-ID) -> 403 Forbidden
    res_no_auth = client.get(f"/trip/{trip_id}")
    assert res_no_auth.status_code == 403
    assert "Access denied" in res_no_auth.json().get("detail", "")

    # 2. Stranger request (different X-User-ID) -> 403 Forbidden
    res_stranger = client.get(f"/trip/{trip_id}", headers={"X-User-ID": stranger_id})
    assert res_stranger.status_code == 403
    assert "Access denied" in res_stranger.json().get("detail", "")

    # 3. Stranger tries to export or view calendar -> 403 Forbidden
    res_export = client.get(f"/trip/{trip_id}/export", headers={"X-User-ID": stranger_id})
    assert res_export.status_code == 403

    res_cal = client.get(f"/trip/{trip_id}/calendar", headers={"X-User-ID": stranger_id})
    assert res_cal.status_code == 403

    # 4. Owner request with X-User-ID -> 200 OK
    res_owner = client.get(f"/trip/{trip_id}", headers={"X-User-ID": owner_id})
    assert res_owner.status_code == 200
    data = res_owner.json()
    assert data["trip_id"] == trip_id
    assert data["role"] == "owner"
    assert data["owner_id"] == owner_id


def test_guessing_random_trip_id_returns_404():
    """Accessing non-existent trip ID returns 404, not unauthorized."""
    res = client.get("/trip/non-existent-uuid-12345", headers={"X-User-ID": "anyone"})
    assert res.status_code == 404


# =====================================================================
# 2. Cryptographic Token Hashing & Invitations Foundation
# =====================================================================

def test_invitation_token_creation_and_hash_storage():
    """Raw token is returned once, while trips storage stores only the SHA-256 hash."""
    owner_id = "user_inv_owner"
    payload = _sample_trip_payload("Kerala", "Bengaluru")
    trip_id = save_trip(payload, owner_id=owner_id)

    # Create viewer invitation via API
    res = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "viewer", "expires_in_days": 7},
        headers={"X-User-ID": owner_id},
    )
    assert res.status_code == 201
    inv_data = res.json()
    assert "token" in inv_data
    raw_token = inv_data["token"]
    assert len(raw_token) >= 32  # Cryptographically secure unguessable token
    assert inv_data["role"] == "viewer"
    assert inv_data["status"] == "pending"

    # Verify JSON persistence in trips.json: raw token MUST NOT be stored!
    record = load_trip_record(trip_id)
    invitations = record.get("invitations", [])
    assert len(invitations) >= 1
    stored_inv = next(i for i in invitations if i["invitation_id"] == inv_data["invitation_id"])

    assert "token" not in stored_inv  # Raw token never stored
    assert stored_inv["token_hash"] == hash_token(raw_token)  # Only SHA-256 hash stored


def test_stranger_cannot_create_invitations():
    """Only trip owner can generate invitations."""
    owner_id = "user_real_owner"
    stranger_id = "user_fake_owner"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    res = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "editor"},
        headers={"X-User-ID": stranger_id},
    )
    assert res.status_code == 403


# =====================================================================
# 3. Viewer vs Editor Role Permissions & Workflow
# =====================================================================

def test_viewer_role_read_allowed_write_forbidden():
    """Viewer can read trip details but write/mutation operations return 403."""
    owner_id = "user_trip_owner"
    viewer_id = "user_invited_viewer"
    trip_id = save_trip(_sample_trip_payload("Delhi", "Agra"), owner_id=owner_id)

    # 1. Owner creates invitation for viewer
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    # 2. Viewer previews invitation without auth
    preview_res = client.get(f"/invitations/{token}")
    assert preview_res.status_code == 200
    assert preview_res.json()["destination"] == "Delhi"
    assert preview_res.json()["role"] == "viewer"
    assert preview_res.json()["valid"] is True

    # 3. Viewer accepts invitation
    accept_res = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": viewer_id})
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"
    assert accept_res.json()["role"] == "viewer"

    # 4. Viewer can read trip
    view_res = client.get(f"/trip/{trip_id}", headers={"X-User-ID": viewer_id})
    assert view_res.status_code == 200
    assert view_res.json()["role"] == "viewer"

    # 5. Viewer attempts to mutate trip via PATCH /trip/{trip_id} -> 403 Forbidden
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add a museum stop"},
        headers={"X-User-ID": viewer_id},
    )
    assert patch_res.status_code == 403
    assert "Permission denied" in patch_res.json().get("detail", "")

    # 6. Viewer attempts to add attraction action -> 403 Forbidden
    action_res = client.post(
        f"/trip/{trip_id}/attraction-action",
        json={"day": "1", "attraction_name": "Baga Beach", "action": "remove"},
        headers={"X-User-ID": viewer_id},
    )
    assert action_res.status_code == 403

    # 7. Viewer attempts to add note -> 403 Forbidden
    note_res = client.post(
        f"/trip/{trip_id}/notes",
        json={"note": "Viewer cannot add notes"},
        headers={"X-User-ID": viewer_id},
    )
    assert note_res.status_code == 403

    # 8. Viewer attempts to create invitation -> 403 Forbidden
    inv_res = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "viewer"},
        headers={"X-User-ID": viewer_id},
    )
    assert inv_res.status_code == 403


def test_editor_role_read_and_edit_allowed_cannot_invite():
    """Editor can read and edit activities, but cannot invite or revoke."""
    owner_id = "user_collab_owner"
    editor_id = "user_collab_editor"
    trip_id = save_trip(_sample_trip_payload("Jaipur", "Delhi"), owner_id=owner_id)

    # 1. Owner invites editor
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="editor")
    token = inv["token"]

    # 2. Editor accepts invitation
    accept_res = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": editor_id})
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "editor"

    # 3. Editor can read trip
    view_res = client.get(f"/trip/{trip_id}", headers={"X-User-ID": editor_id})
    assert view_res.status_code == 200
    assert view_res.json()["role"] == "editor"

    # 4. Editor can add note
    note_res = client.post(
        f"/trip/{trip_id}/notes",
        json={"note": "Editor verified addition"},
        headers={"X-User-ID": editor_id},
    )
    assert note_res.status_code == 200

    # 5. Editor cannot manage invitations (owner only) -> 403 Forbidden
    inv_res = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "viewer"},
        headers={"X-User-ID": editor_id},
    )
    assert inv_res.status_code == 403


# =====================================================================
# 4. Expiration, Revocation, and Decline Tests
# =====================================================================

def test_expired_invitation_cannot_be_accepted():
    """Invitations past their expiration date return 400 Bad Request."""
    owner_id = "user_exp_owner"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # Create an invitation that expired in the past
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer", expires_in_days=1)
    token = inv["token"]

    # Force expiration by updating expires_at to 2 days ago
    record = load_trip_record(trip_id)
    token_hash = hash_token(token)
    for i in record["invitations"]:
        if i["token_hash"] == token_hash:
            i["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    update_trip_sharing(trip_id, invitations=record["invitations"])

    # Preview reflects expired status
    prev = client.get(f"/invitations/{token}").json()
    assert prev["valid"] is False
    assert prev["status"] == "expired"

    # Attempt accept -> 400 Bad Request
    res = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": "user_late"})
    assert res.status_code == 400
    assert "expired" in res.json().get("detail", "").lower()


def test_revoked_invitation_cannot_be_accepted():
    """Revoked invitations cannot be accepted."""
    owner_id = "user_rev_owner"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]
    inv_id = inv["invitation_id"]

    # Owner revokes invitation
    del_res = client.delete(f"/trip/{trip_id}/invitations/{inv_id}", headers={"X-User-ID": owner_id})
    assert del_res.status_code == 200

    # Attempt accept -> 400 Bad Request
    res = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": "user_hopeful"})
    assert res.status_code == 400
    assert "revoked" in res.json().get("detail", "").lower()


def test_declined_invitation():
    """Invitee can decline an invitation."""
    owner_id = "user_dec_owner"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    dec_res = client.post(f"/invitations/{token}/decline", headers={"X-User-ID": "user_polite"})
    assert dec_res.status_code == 200
    assert dec_res.json()["status"] == "declined"

    # Trying to accept declined invitation returns 400
    acc_res = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": "user_polite"})
    assert acc_res.status_code == 400


# =====================================================================
# 5. Trip History Isolation
# =====================================================================

def test_trip_history_isolates_private_trips():
    """Users only see their own trips and shared trips in trip history."""
    user_a = "user_history_a"
    user_b = "user_history_b"

    trip_a = save_trip(_sample_trip_payload("Ladakh", "Delhi"), owner_id=user_a)
    trip_b = save_trip(_sample_trip_payload("Ooty", "Chennai"), owner_id=user_b)

    # History for user_a should contain trip_a, not trip_b
    res_a = client.get("/trip/history", headers={"X-User-ID": user_a})
    assert res_a.status_code == 200
    ids_a = [t["id"] for t in res_a.json().get("trips", [])]
    assert trip_a in ids_a
    assert trip_b not in ids_a

    # History for user_b should contain trip_b, not trip_a
    res_b = client.get("/trip/history", headers={"X-User-ID": user_b})
    assert res_b.status_code == 200
    ids_b = [t["id"] for t in res_b.json().get("trips", [])]
    assert trip_b in ids_b
    assert trip_a not in ids_b


# =====================================================================
# 6. Concurrency Safety Tests
# =====================================================================

def test_concurrent_updates_do_not_corrupt_store():
    """Multiple threads updating trip sharing concurrently operate safely under lock."""
    owner_id = "user_concurrent_owner"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    errors = []

    def create_worker(idx):
        try:
            create_invitation(trip_id, owner_id, role="viewer")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=create_worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    record = load_trip_record(trip_id)
    assert len(record.get("invitations", [])) == 10


# =====================================================================
# 7. Backward Compatibility: Legacy Unowned Trips
# =====================================================================

def test_legacy_unowned_trip_remains_accessible():
    """Trips created without an owner (pre-Step 75 legacy data) remain accessible."""
    payload = _sample_trip_payload("Manali", "Chandigarh")
    trip_id = save_trip(payload, owner_id=None)

    # Anyone can access legacy unowned trip without credentials
    res = client.get(f"/trip/{trip_id}")
    assert res.status_code == 200
    assert res.json()["trip_id"] == trip_id
