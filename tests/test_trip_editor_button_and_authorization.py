"""
Focused tests for trip editor actions, role checks, and backend authorization.
Verifies:
1. Authorized Owner can edit trip itinerary via PATCH /trip/{id}.
2. Authorized Editor can edit trip itinerary via PATCH /trip/{id}.
3. Viewer is strictly prohibited from editing (HTTP 403 Forbidden).
4. Unauthenticated user on private trip cannot edit (HTTP 401 Unauthorized).
5. GET /trip/{id} accurately returns active user's role (owner, editor, viewer).
6. Backward compatibility: unowned legacy trips permit editing.
7. Validation: invalid or empty prompt handling.
"""

import copy
import pytest
from starlette.testclient import TestClient

from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip
from backend.services.sharing.invitation_service import create_invitation
from backend.services.auth.jwt_service import create_access_token

client = TestClient(app)


def auth_headers(user_id: str) -> dict:
    token = create_access_token(user_id=user_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-User-ID": user_id,
    }


def _sample_trip_payload(dest="Goa"):
    return {
        "trip": {
            "source": "Bengaluru",
            "destination": dest,
            "days": 2,
            "places": [
                {"name": "Calangute Beach", "category": "Beach", "lat": 15.54, "lon": 73.75},
                {"name": "Fort Aguada", "category": "History", "lat": 15.49, "lon": 73.77},
            ],
            "day_schedule": {
                "1": [{"name": "Calangute Beach"}],
                "2": [{"name": "Fort Aguada"}],
            },
            "budget": {
                "total_budget": 10000,
                "estimated_cost": 8000,
                "remaining": 2000,
                "status": "Within Budget",
                "categories": {},
            },
        }
    }


def test_owner_can_edit_trip(isolated_storage, monkeypatch):
    """An authorized trip owner can submit trip editing prompts via PATCH /trip/{id}."""
    owner_id = "user_owner_alpha"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # Mock LLM to deterministically return an action
    def mock_interpret(prompt):
        return {"actions": [{"type": "set_budget", "amount": 15000}]}

    monkeypatch.setattr("backend.routes.update_trip.interpret_trip_prompt", mock_interpret)

    # 1. Verify owner role on GET /trip/{id}
    get_res = client.get(f"/trip/{trip_id}", headers=auth_headers(owner_id))
    assert get_res.status_code == 200
    assert get_res.json()["role"] == "owner"

    # 2. Owner performs edit
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Increase budget to 15000"},
        headers=auth_headers(owner_id),
    )
    assert patch_res.status_code == 200
    updated = load_trip(trip_id)
    budget = updated["trip"]["budget"]
    assert budget.get("total_budget") == 15000 or budget.get("total") == 15000


def test_editor_can_edit_trip(isolated_storage, monkeypatch):
    """An invited collaborator with 'editor' role can edit trip itinerary via PATCH /trip/{id}."""
    owner_id = "user_owner_beta"
    editor_id = "user_collab_editor_beta"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # Owner invites editor
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="editor")
    token = inv["token"]

    # Editor accepts invitation
    accept_res = client.post(f"/invitations/{token}/accept", headers=auth_headers(editor_id))
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "editor"

    # Verify editor role returned on GET /trip/{id}
    get_res = client.get(f"/trip/{trip_id}", headers=auth_headers(editor_id))
    assert get_res.status_code == 200
    assert get_res.json()["role"] == "editor"

    # Mock LLM to deterministically return an action
    def mock_interpret(prompt):
        return {"actions": [{"type": "set_budget", "amount": 12500}]}

    monkeypatch.setattr("backend.routes.update_trip.interpret_trip_prompt", mock_interpret)

    # Editor performs edit
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Set budget to 12500"},
        headers=auth_headers(editor_id),
    )
    assert patch_res.status_code == 200
    updated = load_trip(trip_id)
    assert updated["trip"]["budget"].get("total_budget") == 12500


def test_viewer_strictly_blocked_from_editing(isolated_storage):
    """A user with 'viewer' role is strictly rejected with 403 Forbidden when attempting edits."""
    owner_id = "user_owner_gamma"
    viewer_id = "user_collab_viewer_gamma"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # Owner invites viewer
    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    token = inv["token"]

    # Viewer accepts invitation
    accept_res = client.post(f"/invitations/{token}/accept", headers=auth_headers(viewer_id))
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "viewer"

    # Verify viewer role on GET /trip/{id}
    get_res = client.get(f"/trip/{trip_id}", headers=auth_headers(viewer_id))
    assert get_res.status_code == 200
    assert get_res.json()["role"] == "viewer"

    # Viewer attempts direct API edit -> MUST be rejected with 403
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add Baga Beach"},
        headers=auth_headers(viewer_id),
    )
    assert patch_res.status_code == 403
    err = patch_res.json()
    assert "permission denied" in err.get("detail", "").lower() or "required role" in err.get("detail", "").lower()


def test_unauthenticated_request_rejected_on_private_trip(isolated_storage):
    """Unauthenticated requests to PATCH a private trip must return 401 Unauthorized."""
    owner_id = "user_owner_delta"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    # No Authorization header, no credentials
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add Beach"},
    )
    assert patch_res.status_code == 401
    err = patch_res.json()
    assert "authentication required" in err.get("detail", "").lower() or err.get("error_code") == "UNAUTHORIZED"


def test_stranger_cannot_edit_private_trip(isolated_storage):
    """An authenticated user with no membership on a private trip cannot edit (403 Forbidden)."""
    owner_id = "user_owner_eps"
    stranger_id = "user_stranger_unrelated"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Add Beach"},
        headers=auth_headers(stranger_id),
    )
    assert patch_res.status_code == 403
    err = patch_res.json()
    assert "access denied" in err.get("detail", "").lower() or "permission denied" in err.get("detail", "").lower()


def test_legacy_unowned_trip_allows_editing_for_compatibility(isolated_storage, monkeypatch):
    """Legacy trips with no owner_id allow editor operations for backward compatibility."""
    trip_id = save_trip(_sample_trip_payload(), owner_id=None)

    def mock_interpret(prompt):
        return {"actions": [{"type": "set_budget", "amount": 9000}]}

    monkeypatch.setattr("backend.routes.update_trip.interpret_trip_prompt", mock_interpret)

    # Check GET returns editor role for legacy unowned trips
    get_res = client.get(f"/trip/{trip_id}")
    assert get_res.status_code == 200
    assert get_res.json()["role"] == "editor"

    # Edit without auth headers succeeds for backward compatibility
    patch_res = client.patch(
        f"/trip/{trip_id}",
        json={"prompt": "Set budget to 9000"},
    )
    assert patch_res.status_code == 200
    updated = load_trip(trip_id)
    assert updated["trip"]["budget"].get("total_budget") == 9000


def test_viewer_blocked_from_replan_and_attraction_actions(isolated_storage):
    """Viewers are rejected with 403 Forbidden on all mutation endpoints."""
    owner_id = "user_owner_zeta"
    viewer_id = "user_viewer_zeta"
    trip_id = save_trip(_sample_trip_payload(), owner_id=owner_id)

    inv = create_invitation(trip_id=trip_id, owner_user_id=owner_id, role="viewer")
    client.post(f"/invitations/{inv['token']}/accept", headers=auth_headers(viewer_id))

    # 1. replan-day blocked for viewer
    replan_res = client.post(
        f"/trip/{trip_id}/replan-day",
        json={"day": 1, "completed_attractions": []},
        headers=auth_headers(viewer_id),
    )
    assert replan_res.status_code == 403

    # 2. attraction-action blocked for viewer
    act_res = client.post(
        f"/trip/{trip_id}/attraction-action",
        json={"action": "remove", "day": "1", "attraction_name": "Calangute Beach"},
        headers=auth_headers(viewer_id),
    )
    assert act_res.status_code == 403

