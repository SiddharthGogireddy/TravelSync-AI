"""
Comprehensive regression tests for TravelSync AI invitation acceptance flow.

Covers requirements:
1. Missing user ID / unauthenticated acceptance rejected (400 / 401).
2. Valid acceptance using authenticated Bearer token and matching X-User-ID.
3. Preserves intended role: Viewer remains Viewer (read-only), Editor gets Editor.
4. Rejects expired invitation tokens (400 Bad Request).
5. Rejects invalid or nonexistent tokens (404 Not Found).
6. Confused-deputy defense: rejecting mismatched token subject vs declared X-User-ID.
7. Public preview endpoint remains accessible without credentials.
"""

import copy
from datetime import datetime, timezone, timedelta
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


def test_missing_user_id_rejected_on_acceptance(isolated_storage):
    """Calling accept without an authenticated session or user ID returns 400 Bad Request."""
    owner_id = "user_owner_reg1"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    # 1. No headers at all -> 400 Bad Request
    res_no_headers = client.post(f"/invitations/{token}/accept")
    assert res_no_headers.status_code == 400
    assert "user id is required" in res_no_headers.json().get("detail", "").lower()

    # 2. Empty string X-User-ID -> 400 Bad Request
    res_empty_header = client.post(
        f"/invitations/{token}/accept",
        headers={"X-User-ID": "   "},
    )
    assert res_empty_header.status_code == 400
    assert "user id is required" in res_empty_header.json().get("detail", "").lower()


def test_valid_viewer_acceptance_and_permission_enforcement(isolated_storage):
    """A guest session with a valid Bearer token accepts a Viewer invitation and is strictly restricted."""
    owner_id = "user_owner_reg2"
    viewer_id = "user_guest_viewer_2026"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    # Preview is public and readable
    preview_res = client.get(f"/invitations/{token}")
    assert preview_res.status_code == 200
    assert preview_res.json()["role"] == "viewer"
    assert preview_res.json()["destination"] == "Hyderabad"

    # Guest accepts invitation
    accept_res = client.post(
        f"/invitations/{token}/accept",
        headers=auth_headers(viewer_id),
    )
    assert accept_res.status_code == 200
    data = accept_res.json()
    assert data["status"] == "accepted"
    assert data["trip_id"] == trip_id
    assert data["role"] == "viewer"

    # Membership verified in storage
    record = load_trip_record(trip_id)
    assert viewer_id in record.get("members", {})
    assert record["members"][viewer_id]["role"] == "viewer"

    # Viewer can read trip
    trip_res = client.get(f"/trip/{trip_id}", headers=auth_headers(viewer_id))
    assert trip_res.status_code == 200
    assert trip_res.json()["role"] == "viewer"

    # Viewer strictly cannot edit
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add Birla Mandir"},
        headers=auth_headers(viewer_id),
    )
    assert patch_res.status_code == 403
    assert "permission denied" in patch_res.json().get("detail", "").lower() or "required role" in patch_res.json().get("detail", "").lower()


def test_valid_editor_acceptance_preserves_editor_role(isolated_storage):
    """An Editor invitation assigns Editor role, allowing edits but blocking owner invite actions."""
    owner_id = "user_owner_reg3"
    editor_id = "user_guest_editor_2026"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="editor")
    token = inv["token"]

    accept_res = client.post(
        f"/invitations/{token}/accept",
        headers=auth_headers(editor_id),
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "editor"

    # Editor can view
    trip_res = client.get(f"/trip/{trip_id}", headers=auth_headers(editor_id))
    assert trip_res.status_code == 200
    assert trip_res.json()["role"] == "editor"

    # Editor cannot create new invitations (owner only)
    inv_res = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "viewer"},
        headers=auth_headers(editor_id),
    )
    assert inv_res.status_code == 403


def test_expired_token_acceptance_rejected(isolated_storage):
    """An invitation that is past its expiration date is rejected with 400 Bad Request."""
    owner_id = "user_owner_reg4"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    # Manually backdate the invitation in storage
    from backend.services.sharing.invitation_service import hash_token
    record = load_trip_record(trip_id)
    token_hash = hash_token(token)
    for i in record.get("invitations", []):
        if i.get("token_hash") == token_hash:
            i["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    from backend.services.storage.trip_store import _STORE_LOCK, _read_trips, _write_trips
    with _STORE_LOCK:
        all_trips = _read_trips()
        for t in all_trips:
            if t.get("id") == trip_id:
                t["invitations"] = record["invitations"]
        _write_trips(all_trips)

    # Acceptance fails with expired error
    res = client.post(
        f"/invitations/{token}/accept",
        headers=auth_headers("user_late_guest"),
    )
    assert res.status_code == 400
    assert "expired" in res.json().get("detail", "").lower()


def test_invalid_or_nonexistent_token_rejected(isolated_storage):
    """Accepting a bogus token returns 404 Not Found."""
    res = client.post(
        "/invitations/fake_nonexistent_token_12345/accept",
        headers=auth_headers("some_user"),
    )
    assert res.status_code == 404
    assert "invalid invitation" in res.json().get("detail", "").lower()


def test_confused_deputy_header_token_mismatch_rejected(isolated_storage):
    """Passing a token for User A with X-User-ID claiming to be User B returns 401 Unauthorized."""
    owner_id = "user_owner_reg5"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    # Token signed for user_alice, but X-User-ID spoofed as user_bob
    token_alice = create_access_token(user_id="user_alice")
    mismatched_headers = {
        "Authorization": f"Bearer {token_alice}",
        "X-User-ID": "user_bob",
    }

    res = client.post(f"/invitations/{token}/accept", headers=mismatched_headers)
    assert res.status_code == 401
    assert "mismatch" in res.json().get("detail", "").lower()


def test_accepted_viewer_and_editor_access_notes_and_insights(isolated_storage):
    """
    Regression verification for Step 75.3:
    Verifies that newly accepted Viewer and Editor sessions can read:
    - GET /trip/{trip_id}/notes
    - GET /trip/{trip_id}/insights
    without 401 Unauthorized errors when passing standard Bearer JWT and X-User-ID.
    """
    owner_id = "user_owner_reg6"
    viewer_id = "user_accepted_viewer_notes"
    editor_id = "user_accepted_editor_notes"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # 1. Viewer acceptance
    inv_v = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token_v = inv_v["token"]
    res_v_accept = client.post(f"/invitations/{token_v}/accept", headers=auth_headers(viewer_id))
    assert res_v_accept.status_code == 200
    assert res_v_accept.json()["role"] == "viewer"

    # 2. Viewer accesses notes -> 200 OK
    res_v_notes = client.get(f"/trip/{trip_id}/notes", headers=auth_headers(viewer_id))
    assert res_v_notes.status_code == 200
    assert "notes" in res_v_notes.json()

    # 3. Viewer accesses insights -> 200 OK
    res_v_insights = client.get(f"/trip/{trip_id}/insights", headers=auth_headers(viewer_id))
    assert res_v_insights.status_code == 200
    assert "metrics" in res_v_insights.json()

    # 4. Editor acceptance
    inv_e = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="editor")
    token_e = inv_e["token"]
    res_e_accept = client.post(f"/invitations/{token_e}/accept", headers=auth_headers(editor_id))
    assert res_e_accept.status_code == 200
    assert res_e_accept.json()["role"] == "editor"

    # 5. Editor accesses notes and insights -> 200 OK
    res_e_notes = client.get(f"/trip/{trip_id}/notes", headers=auth_headers(editor_id))
    assert res_e_notes.status_code == 200

    res_e_insights = client.get(f"/trip/{trip_id}/insights", headers=auth_headers(editor_id))
    assert res_e_insights.status_code == 200

    # 6. Unauthenticated requests to notes and insights -> 401 Unauthorized
    res_unauth_notes = client.get(f"/trip/{trip_id}/notes")
    assert res_unauth_notes.status_code == 401

    res_unauth_insights = client.get(f"/trip/{trip_id}/insights")
    assert res_unauth_insights.status_code == 401


def test_accepted_viewer_and_editor_access_expenses(isolated_storage):
    """
    Regression verification for Step 75.4:
    Verifies that newly accepted Viewer and Editor sessions can read:
    - GET /expense/{trip_id}
    when passing standard Bearer JWT and X-User-ID, while unauthenticated calls return 401.
    """
    owner_id = "user_owner_reg7"
    viewer_id = "user_accepted_viewer_expenses"
    editor_id = "user_accepted_editor_expenses"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # 1. Viewer acceptance
    inv_v = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token_v = inv_v["token"]
    res_v_accept = client.post(f"/invitations/{token_v}/accept", headers=auth_headers(viewer_id))
    assert res_v_accept.status_code == 200

    # 2. Viewer accesses expenses -> 200 OK
    res_v_exp = client.get(f"/expense/{trip_id}", headers=auth_headers(viewer_id))
    assert res_v_exp.status_code == 200
    assert "expenses" in res_v_exp.json()
    assert "balances" in res_v_exp.json()

    # 3. Editor acceptance & accesses expenses -> 200 OK
    inv_e = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="editor")
    token_e = inv_e["token"]
    res_e_accept = client.post(f"/invitations/{token_e}/accept", headers=auth_headers(editor_id))
    assert res_e_accept.status_code == 200

    res_e_exp = client.get(f"/expense/{trip_id}", headers=auth_headers(editor_id))
    assert res_e_exp.status_code == 200

    # 4. Unauthenticated call -> 401 Unauthorized
    res_unauth_exp = client.get(f"/expense/{trip_id}")
    assert res_unauth_exp.status_code == 401

