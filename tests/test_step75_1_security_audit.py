import os
import sys
import pytest
import concurrent.futures
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip_record, _STORE_LOCK
from backend.services.sharing.invitation_service import create_invitation, hash_token

from backend.services.auth.jwt_service import create_access_token
from backend.services.auth.authorization import _sanitize_user_id


class HardenedAuditClient(TestClient):
    def request(self, method: str, url: str, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        raw_mode = headers.pop("_raw_unauthenticated", None)
        if "X-User-ID" in headers and "Authorization" not in headers and not raw_mode:
            clean_uid = _sanitize_user_id(headers["X-User-ID"])
            if clean_uid:
                token = create_access_token(user_id=clean_uid)
                headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers
        elif raw_mode:
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


client = HardenedAuditClient(app)

SAMPLE_TRIP = {
    "source": "Mumbai",
    "destination": "Goa",
    "days": 3,
    "budget": {"total_budget": 15000, "estimated_cost": 12000},
    "travelers": [{"name": "Alice", "interests": ["Beach"]}],
    "day_schedule": {
        "1": [{"name": "Calangute Beach", "category": "Beach"}],
        "2": [{"name": "Fort Aguada", "category": "Heritage"}],
        "3": [{"name": "Anjuna Beach", "category": "Beach"}],
    },
    "places": [
        {"name": "Calangute Beach", "category": "Beach"},
        {"name": "Fort Aguada", "category": "Heritage"},
        {"name": "Anjuna Beach", "category": "Beach"},
    ],
}


def create_test_trip(owner_id: str = "owner_alice"):
    payload = {
        "trip": dict(SAMPLE_TRIP),
        "dashboard": {"destination": "Goa", "days": 3},
        "summary": {"days": 3},
    }
    trip_id = save_trip(payload, owner_id=owner_id)
    return trip_id


# ---------------------------------------------------------------------------
# Check 1: X-User-ID Impersonation Hardening & Credential Verification
# ---------------------------------------------------------------------------
def test_check_1_header_spoofing_impersonation_demonstration():
    """
    Step 75.2 Hardening Verification:
    Demonstrates that client-declared X-User-ID headers are NEVER trusted as proof of identity.
    Derives identity exclusively from verified Bearer credentials.
    """
    trip_id = create_test_trip(owner_id="victim_alice")

    # 1. Stranger with valid token for attacker_bob is blocked from victim_alice's trip -> 403 Forbidden
    resp_stranger = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "attacker_bob"})
    assert resp_stranger.status_code == 403

    # 2. Attacker passing forged X-User-ID without valid Bearer token -> 401 Unauthorized
    resp_spoofed = client.get(
        f"/trip/{trip_id}",
        headers={"X-User-ID": "victim_alice", "_raw_unauthenticated": "true"}
    )
    assert resp_spoofed.status_code == 401
    assert "Authentication required" in resp_spoofed.json().get("detail", "")

    # 3. Attacker with valid bob token spoofing victim_alice in X-User-ID -> 401 Identity Mismatch
    bob_token = create_access_token(user_id="attacker_bob")
    resp_mismatch = client.get(
        f"/trip/{trip_id}",
        headers={"Authorization": f"Bearer {bob_token}", "X-User-ID": "victim_alice"}
    )
    assert resp_mismatch.status_code == 401
    assert "mismatch" in resp_mismatch.json().get("detail", "").lower()

    # 4. Legitimate owner with valid Bearer token -> 200 OK
    resp_owner = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "victim_alice"})
    assert resp_owner.status_code == 200
    assert resp_owner.json()["trip_id"] == trip_id



# ---------------------------------------------------------------------------
# Check 2: Server-Side Authorization Enforcement on All Private Endpoints
# ---------------------------------------------------------------------------
def test_check_2_pdf_download_authorization_enforced():
    """Verify that GET /trip/{trip_id}/pdf requires authorization."""
    trip_id = create_test_trip(owner_id="alice")

    # Stranger blocked
    resp = client.get(f"/trip/{trip_id}/pdf", headers={"X-User-ID": "bob"})
    assert resp.status_code == 403

    # Owner allowed
    resp = client.get(f"/trip/{trip_id}/pdf", headers={"X-User-ID": "alice"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_check_2_template_creation_authorization_enforced():
    """Verify that POST /templates/from-trip/{trip_id} enforces viewer authorization."""
    trip_id = create_test_trip(owner_id="alice")

    # Stranger blocked
    resp = client.post(
        f"/templates/from-trip/{trip_id}",
        json={"name": "Stolen Template"},
        headers={"X-User-ID": "bob"}
    )
    assert resp.status_code == 403

    # Owner allowed
    resp = client.post(
        f"/templates/from-trip/{trip_id}",
        json={"name": "Alice Template"},
        headers={"X-User-ID": "alice"}
    )
    assert resp.status_code == 200
    assert resp.json()["template_id"].startswith("tpl_")


def test_check_2_explanation_route_authorization_enforced():
    """Verify that POST /explanation/{trip_id} enforces authorization."""
    trip_id = create_test_trip(owner_id="alice")

    # Stranger blocked
    resp = client.post(
        f"/explanation/{trip_id}",
        json={"place_name": "Calangute Beach"},
        headers={"X-User-ID": "bob"}
    )
    assert resp.status_code == 403

    # Owner allowed
    resp = client.post(
        f"/explanation/{trip_id}",
        json={"place_name": "Calangute Beach"},
        headers={"X-User-ID": "alice"}
    )
    assert resp.status_code == 200


def test_check_2_group_collaboration_and_chat_authorization_enforced():
    """Verify group-vote, resolve-group-conflicts, and assistant-chat routes enforce authorization."""
    trip_id = create_test_trip(owner_id="alice")

    # Group vote: stranger blocked (403)
    resp = client.post(
        f"/trip/{trip_id}/group-vote",
        json={"traveler_name": "Alice", "attraction_name": "Calangute Beach", "vote": "up"},
        headers={"X-User-ID": "stranger"}
    )
    assert resp.status_code == 403

    # Owner can vote
    resp = client.post(
        f"/trip/{trip_id}/group-vote",
        json={"traveler_name": "Alice", "attraction_name": "Calangute Beach", "vote": "up"},
        headers={"X-User-ID": "alice"}
    )
    assert resp.status_code == 200

    # Resolve conflicts: stranger blocked (403)
    resp = client.post(
        f"/trip/{trip_id}/resolve-group-conflicts",
        headers={"X-User-ID": "stranger"}
    )
    assert resp.status_code == 403

    # Assistant chat: stranger blocked (403)
    resp = client.post(
        f"/trip/{trip_id}/assistant-chat",
        json={"message": "What is the plan?"},
        headers={"X-User-ID": "stranger"}
    )
    assert resp.status_code == 403

    # Owner allowed to chat
    resp = client.post(
        f"/trip/{trip_id}/assistant-chat",
        json={"message": "What is the plan for day 1?"},
        headers={"X-User-ID": "alice"}
    )
    assert resp.status_code == 200


def test_check_2_trip_compare_enforces_authorization_for_both_trips():
    """Verify GET /trip/compare enforces access to both trips."""
    trip_1 = create_test_trip(owner_id="alice")
    trip_2 = create_test_trip(owner_id="alice")
    trip_private_bob = create_test_trip(owner_id="bob")

    # Alice can compare her own two trips
    resp = client.get(f"/trip/compare?trip1={trip_1}&trip2={trip_2}", headers={"X-User-ID": "alice"})
    assert resp.status_code == 200

    # Alice cannot compare her trip with Bob's private trip
    resp = client.get(f"/trip/compare?trip1={trip_1}&trip2={trip_private_bob}", headers={"X-User-ID": "alice"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Check 3: Invitation Token Security & Concurrent Acceptance Race Safety
# ---------------------------------------------------------------------------
def test_check_3_token_entropy_and_hash_storage():
    """Verify invitation token generation has high entropy and stores only hashes."""
    trip_id = create_test_trip(owner_id="alice")
    inv = create_invitation(trip_id, "alice", role="viewer")
    raw_token = inv["token"]

    # Minimum 32 chars urlsafe (256 bits entropy)
    assert len(raw_token) >= 32

    # Storage check: only token_hash is stored
    rec = load_trip_record(trip_id)
    invitations = rec.get("invitations", [])
    assert len(invitations) >= 1
    stored_inv = invitations[-1]
    assert "raw_token" not in stored_inv
    assert "token" not in stored_inv
    assert stored_inv["token_hash"] == hash_token(raw_token)


def test_check_3_concurrent_invitation_acceptance_race_condition():
    """
    Spawns multiple concurrent threads attempting to accept the exact same invitation.
    Verifies that atomic locking ensures exactly ONE thread succeeds and the rest receive 400.
    """
    trip_id = create_test_trip(owner_id="alice")
    inv = create_invitation(trip_id, "alice", role="editor")
    raw_token = inv["token"]

    results = []

    def try_accept(user_idx):
        user_id = f"concurrent_user_{user_idx}"
        resp = client.post(
            f"/invitations/{raw_token}/accept",
            headers={"X-User-ID": user_id}
        )
        return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(try_accept, i) for i in range(8)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # Exactly 1 success (200) and 7 failures (400 - already accepted)
    assert results.count(200) == 1
    assert results.count(400) == 7


# ---------------------------------------------------------------------------
# Check 4: Public Invitation Preview Information Disclosure
# ---------------------------------------------------------------------------
def test_check_4_preview_does_not_leak_private_details():
    """Verify that public preview does not disclose sensitive private trip data."""
    trip_id = create_test_trip(owner_id="alice")
    inv = create_invitation(trip_id, "alice", role="viewer")
    raw_token = inv["token"]

    preview_resp = client.get(f"/invitations/{raw_token}/preview")
    assert preview_resp.status_code == 200
    preview = preview_resp.json()

    # Destination and duration are allowed for context
    assert preview["destination"] == "Goa"
    assert preview["days"] == 3
    assert preview["role"] == "viewer"
    assert preview["valid"] is True

    # Must NOT leak travelers, notes, budget, day_schedule, places, or owner_id
    assert "travelers" not in preview
    assert "notes" not in preview
    assert "budget" not in preview
    assert "day_schedule" not in preview
    assert "places" not in preview
    assert "owner_id" not in preview


def test_check_4_revoked_and_expired_preview_redaction():
    """Verify that revoked invitation preview redacts destination and source."""
    trip_id = create_test_trip(owner_id="alice")
    inv = create_invitation(trip_id, "alice", role="viewer")
    raw_token = inv["token"]

    # Revoke invitation
    client.delete(f"/trip/{trip_id}/invitations/{inv['invitation_id']}", headers={"X-User-ID": "alice"})

    # Preview revoked invitation
    resp = client.get(f"/invitations/{raw_token}/preview")
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["valid"] is False
    assert preview["status"] == "revoked"
    assert "Revoked" in preview["destination"]
    assert preview["trip_id"] is None


# ---------------------------------------------------------------------------
# Check 5: Legacy Unowned Trips Access Control
# ---------------------------------------------------------------------------
def test_check_5_legacy_unowned_trips_behavior():
    """Verify legacy trips without owner_id grant access as owner for backward compatibility."""
    payload = {
        "trip": dict(SAMPLE_TRIP),
        "dashboard": {"destination": "Goa"},
        "summary": {"days": 3},
    }
    # Save with no owner_id
    trip_id = save_trip(payload, owner_id=None)

    # Any user can read the trip
    resp1 = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "random_user_1"})
    assert resp1.status_code == 200

    resp2 = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "random_user_2"})
    assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# Check 6: Concurrent Writes and Store Integrity
# ---------------------------------------------------------------------------
def test_check_6_concurrent_writes_thread_safety():
    """Verify that concurrent writes to the trip store do not corrupt the JSON store."""
    trip_id = create_test_trip(owner_id="alice")

    def add_note_worker(idx):
        resp = client.post(
            f"/trip/{trip_id}/notes",
            json={"note": f"Concurrent note {idx}"},
            headers={"X-User-ID": "alice"}
        )
        return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(add_note_worker, i) for i in range(6)]
        for f in concurrent.futures.as_completed(futures):
            assert f.result() == 200

    # Ensure all 6 notes were stored cleanly
    notes_resp = client.get(f"/trip/{trip_id}/notes", headers={"X-User-ID": "alice"})
    assert notes_resp.status_code == 200
    assert len(notes_resp.json()["notes"]) == 6


# ---------------------------------------------------------------------------
# Check 7: Ownership Preservation Across Duplication & Template Instantiation
# ---------------------------------------------------------------------------
def test_check_7_template_instantiation_sets_correct_owner():
    """Verify that instantiating a trip from a template assigns ownership to the requester."""
    source_trip = create_test_trip(owner_id="alice")

    # Alice creates a template
    t_resp = client.post(
        f"/templates/from-trip/{source_trip}",
        json={"name": "Goa Trip Template"},
        headers={"X-User-ID": "alice"}
    )
    assert t_resp.status_code == 200
    tpl_id = t_resp.json()["template_id"]

    # Bob instantiates a new trip from the template
    create_resp = client.post(
        f"/templates/{tpl_id}/create-trip",
        json={"budget": 20000},
        headers={"X-User-ID": "bob"}
    )
    assert create_resp.status_code == 200
    new_trip_id = create_resp.json()["trip_id"]

    # Bob owns the new trip
    bob_check = client.get(f"/trip/{new_trip_id}", headers={"X-User-ID": "bob"})
    assert bob_check.status_code == 200

    # Alice does NOT own Bob's new trip (returns 403)
    alice_check = client.get(f"/trip/{new_trip_id}", headers={"X-User-ID": "alice"})
    assert alice_check.status_code == 403


def test_check_7_duplication_assigns_new_owner_and_resets_sensitive_meta():
    """Verify that duplicating a shared trip creates an independent copy owned by the cloner."""
    trip_id = create_test_trip(owner_id="alice")

    # Invite Bob as viewer
    inv = create_invitation(trip_id, "alice", role="viewer")
    client.post(f"/invitations/{inv['token']}/accept", headers={"X-User-ID": "bob"})

    # Bob duplicates the trip
    dup_resp = client.post(f"/trip/{trip_id}/duplicate", headers={"X-User-ID": "bob"})
    assert dup_resp.status_code == 200
    new_trip_id = dup_resp.json()["trip_id"]

    # Bob is the owner of the duplicate
    rec = load_trip_record(new_trip_id)
    assert rec["owner_id"] == "bob"

    # Alice cannot access Bob's duplicated trip unless invited
    alice_resp = client.get(f"/trip/{new_trip_id}", headers={"X-User-ID": "alice"})
    assert alice_resp.status_code == 403


# ---------------------------------------------------------------------------
# Check 1 Extended: User ID Sanitization and Rejection of Malformed IDs
# ---------------------------------------------------------------------------
def test_check_1_user_id_sanitization_and_rejection():
    """Verify that control characters, newlines, and overlong user IDs are sanitized or rejected."""
    trip_id = create_test_trip(owner_id="alice")

    # Empty and whitespace-only user ID is treated as unauthenticated (401 or 403)
    resp_empty = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "   "})
    assert resp_empty.status_code in (401, 403)

    # Overlong user ID (>128 chars) is treated as unauthenticated (401 or 403)
    overlong_id = "a" * 200
    resp_overlong = client.get(f"/trip/{trip_id}", headers={"X-User-ID": overlong_id})
    assert resp_overlong.status_code in (401, 403)

    # Control characters / newlines are stripped
    resp_crlf = client.get(f"/trip/{trip_id}", headers={"X-User-ID": "alice\r\n"})
    assert resp_crlf.status_code == 200


# ---------------------------------------------------------------------------
# Check 2 Extended: Expense Route Server-Side Authorization Enforcement
# ---------------------------------------------------------------------------
def test_check_2_expense_authorization_enforced():
    """Verify that expense viewing requires viewer role and adding expense requires editor role."""
    trip_id = create_test_trip(owner_id="alice")

    # Invite Bob as viewer
    inv_viewer = create_invitation(trip_id, "alice", role="viewer")
    client.post(f"/invitations/{inv_viewer['token']}/accept", headers={"X-User-ID": "bob_viewer"})

    # Invite Charlie as editor
    inv_editor = create_invitation(trip_id, "alice", role="editor")
    client.post(f"/invitations/{inv_editor['token']}/accept", headers={"X-User-ID": "charlie_editor"})

    # 1. Stranger blocked from viewing expenses
    resp = client.get(f"/expense/{trip_id}", headers={"X-User-ID": "stranger"})
    assert resp.status_code == 403

    # 2. Viewer allowed to view expenses
    resp = client.get(f"/expense/{trip_id}", headers={"X-User-ID": "bob_viewer"})
    assert resp.status_code == 200

    # 3. Viewer blocked from adding expense
    resp = client.post(
        "/expense/",
        json={"trip_id": trip_id, "expense": {"title": "Dinner", "amount": 1200, "paid_by": "Bob"}},
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp.status_code == 403

    # 4. Editor allowed to add expense
    resp = client.post(
        "/expense/",
        json={"trip_id": trip_id, "expense": {"title": "Dinner", "amount": 1200, "paid_by": "Charlie"}},
        headers={"X-User-ID": "charlie_editor"}
    )
    assert resp.status_code == 200

    # 5. Missing or empty trip_id is rejected with 400 Bad Request
    resp = client.post(
        "/expense/",
        json={"trip_id": "", "expense": {"title": "Ghost", "amount": 100, "paid_by": "Anyone"}},
        headers={"X-User-ID": "charlie_editor"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Check 2 Extended: Favorites and Ratings Route Server-Side Authorization
# ---------------------------------------------------------------------------
def test_check_2_favorites_and_ratings_authorization_enforced():
    """Verify that favorites and ratings require viewer access and stranger is blocked."""
    trip_id = create_test_trip(owner_id="alice")

    # 1. Stranger blocked from favorite endpoints
    assert client.get(f"/trip/{trip_id}/favorite", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.post(f"/trip/{trip_id}/favorite", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.delete(f"/trip/{trip_id}/favorite", headers={"X-User-ID": "stranger"}).status_code == 403

    # 2. Stranger blocked from rating endpoints
    assert client.get(f"/trip/{trip_id}/rating", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.post(
        f"/trip/{trip_id}/rating",
        json={"rating": 5, "feedback": "Nice"},
        headers={"X-User-ID": "stranger"}
    ).status_code == 403

    # 3. Owner/Viewer allowed
    assert client.post(f"/trip/{trip_id}/favorite", headers={"X-User-ID": "alice"}).status_code == 200
    assert client.get(f"/trip/{trip_id}/favorite", headers={"X-User-ID": "alice"}).status_code == 200
    assert client.post(
        f"/trip/{trip_id}/rating",
        json={"rating": 5, "feedback": "Great trip"},
        headers={"X-User-ID": "alice"}
    ).status_code == 200
    assert client.get(f"/trip/{trip_id}/rating", headers={"X-User-ID": "alice"}).status_code == 200


# ---------------------------------------------------------------------------
# Check 2 Extended: Weather Alerts and Calendar Export Server-Side Authorization
# ---------------------------------------------------------------------------
def test_check_2_weather_alerts_and_calendar_export_authorization_enforced():
    """Verify that weather alerts and calendar ics exports require viewer access."""
    trip_id = create_test_trip(owner_id="alice")

    # 1. Stranger blocked
    assert client.get(f"/weather/trip/{trip_id}/alerts", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.get(f"/trip/{trip_id}/export/calendar.ics", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.get(f"/trip/{trip_id}/export/ics", headers={"X-User-ID": "stranger"}).status_code == 403

    # 2. Owner allowed
    assert client.get(f"/weather/trip/{trip_id}/alerts", headers={"X-User-ID": "alice"}).status_code == 200
    cal_resp = client.get(f"/trip/{trip_id}/export/calendar.ics", headers={"X-User-ID": "alice"})
    assert cal_resp.status_code == 200
    assert "text/calendar" in cal_resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Check 2 Extended: Replanning and Attraction Alternatives/Action Authorization
# ---------------------------------------------------------------------------
def test_check_2_replanning_and_attraction_routes_authorization_enforced():
    """Verify that replanning routes require editor role, while alternatives require viewer role."""
    trip_id = create_test_trip(owner_id="alice")

    inv = create_invitation(trip_id, "alice", role="viewer")
    client.post(f"/invitations/{inv['token']}/accept", headers={"X-User-ID": "bob_viewer"})

    # 1. Attraction alternatives: stranger blocked, viewer allowed
    assert client.get(
        f"/trip/{trip_id}/attraction-alternatives?day=1&attraction_name=Calangute+Beach",
        headers={"X-User-ID": "stranger"}
    ).status_code == 403

    resp_alt = client.get(
        f"/trip/{trip_id}/attraction-alternatives?day=1&attraction_name=Calangute+Beach",
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_alt.status_code == 200

    # 2. Attraction action: viewer blocked (403)
    resp_act = client.post(
        f"/trip/{trip_id}/attraction-action",
        json={"day": "1", "attraction_name": "Calangute Beach", "action": "remove"},
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_act.status_code == 403

    # 3. Optimization score: stranger blocked (403), viewer allowed (200)
    assert client.get(f"/trip/{trip_id}/optimization-score", headers={"X-User-ID": "stranger"}).status_code == 403
    assert client.get(f"/trip/{trip_id}/optimization-score", headers={"X-User-ID": "bob_viewer"}).status_code == 200

    # 4. Optimize trip: viewer blocked (403), owner allowed (200)
    assert client.post(f"/trip/{trip_id}/optimize-trip", headers={"X-User-ID": "bob_viewer"}).status_code == 403
    assert client.post(f"/trip/{trip_id}/optimize-trip", headers={"X-User-ID": "alice"}).status_code == 200


# ---------------------------------------------------------------------------
# Check 3 Extended: Repeated Acceptance & Role Escalation Prevention
# ---------------------------------------------------------------------------
def test_check_3_repeated_acceptance_and_role_escalation_prevention():
    """Verify that accepted invitations cannot be re-accepted and invitations cannot grant owner/admin."""
    trip_id = create_test_trip(owner_id="alice")

    # 1. Disallow creating invitation with non-permitted roles (owner or admin)
    resp_invalid_role = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "owner"},
        headers={"X-User-ID": "alice"}
    )
    assert resp_invalid_role.status_code == 400

    resp_admin = client.post(
        f"/trip/{trip_id}/invitations",
        json={"role": "admin"},
        headers={"X-User-ID": "alice"}
    )
    assert resp_admin.status_code == 400

    # 2. Valid invitation accepted once
    inv = create_invitation(trip_id, "alice", role="viewer")
    token = inv["token"]
    resp_acc1 = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": "user_first"})
    assert resp_acc1.status_code == 200

    # 3. Repeated acceptance by same or another user returns 400
    resp_acc2 = client.post(f"/invitations/{token}/accept", headers={"X-User-ID": "user_second"})
    assert resp_acc2.status_code == 400
    assert "already been accepted" in resp_acc2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Check 6 Extended: Multi-Store Thread Safety
# ---------------------------------------------------------------------------
def test_check_6_concurrent_writes_across_all_stores():
    """Verify concurrent writes across favorites, ratings, and expenses stores remain thread-safe."""
    trip_id = create_test_trip(owner_id="alice")

    from backend.services.storage.favorite_store import add_favorite
    from backend.services.storage.rating_store import save_rating
    from backend.services.expense.expense_store import add_expense

    def worker(idx):
        t_id = f"trip_worker_{idx}"
        add_favorite(t_id)
        save_rating(t_id, 4, f"Feedback {idx}")
        add_expense(t_id, {"title": f"Exp {idx}", "amount": 100 * idx, "paid_by": "Worker"})
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(12)]
        for f in concurrent.futures.as_completed(futures):
            assert f.result() is True
