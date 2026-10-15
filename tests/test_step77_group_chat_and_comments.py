import concurrent.futures
import os
import sys
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, update_trip_sharing
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
    "budget": {"total_budget": 20000, "estimated_cost": 15000},
    "travelers": [{"name": "Alice"}, {"name": "Bob"}],
    "day_schedule": {
        "1": [{"name": "Calangute Beach", "category": "Beach"}],
        "2": [{"name": "Fort Aguada", "category": "Heritage"}],
    },
    "places": [
        {"name": "Calangute Beach", "category": "Beach"},
        {"name": "Fort Aguada", "category": "Heritage"},
    ],
}


def create_trip(owner_id="alice_owner"):
    payload = {
        "trip": dict(SAMPLE_TRIP),
        "dashboard": {"destination": "Goa", "days": 3},
        "summary": {"days": 3},
    }
    trip_id = save_trip(payload, owner_id=owner_id)
    return trip_id


def test_membership_isolation_chat_read():
    """Unauthenticated users and strangers cannot read trip chat."""
    trip_id = create_trip(owner_id="alice_owner")

    # 1. Unauthenticated -> 401
    resp_unauth = client.get(
        f"/chat/{trip_id}",
        headers={"_raw_unauthenticated": "true"}
    )
    assert resp_unauth.status_code == 401

    # 2. Stranger -> 403
    resp_stranger = client.get(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "charlie_stranger"}
    )
    assert resp_stranger.status_code == 403

    # 3. Owner -> 200
    resp_owner = client.get(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_owner.status_code == 200
    assert "messages" in resp_owner.json()
    assert resp_owner.json()["total"] == 0


def test_viewer_can_chat_but_cannot_edit_itinerary():
    """Viewers may participate in chat/discussion but cannot mutate itinerary."""
    trip_id = create_trip(owner_id="alice_owner")

    # Add bob as viewer
    members = {
        "alice_owner": {"role": "owner"},
        "bob_viewer": {"role": "viewer"},
    }
    update_trip_sharing(trip_id, members=members)

    # 1. Viewer posts a chat message -> 201 Created
    resp_chat = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "bob_viewer"},
        json={"content": "Hey everyone, excited for Goa!"}
    )
    assert resp_chat.status_code == 201
    msg_data = resp_chat.json()
    assert msg_data["sender_id"] == "bob_viewer"
    assert msg_data["content"] == "Hey everyone, excited for Goa!"
    assert msg_data["id"] is not None

    # 2. Viewer reads chat messages -> 200 OK
    resp_list = client.get(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_list.status_code == 200
    assert resp_list.json()["total"] == 1
    assert resp_list.json()["messages"][0]["content"] == "Hey everyone, excited for Goa!"

    # 3. Viewer attempts to edit itinerary via resolve-group-conflicts (requires editor) -> 403 Forbidden
    resp_edit = client.post(
        f"/trip/{trip_id}/resolve-group-conflicts",
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_edit.status_code == 403


def test_invalid_messages_rejected():
    """Empty messages, whitespace, and excessive length messages are rejected."""
    trip_id = create_trip(owner_id="alice_owner")

    # Empty string
    resp_empty = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"},
        json={"content": ""}
    )
    assert resp_empty.status_code in (400, 422)

    # Whitespace only
    resp_whitespace = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "     \n   "}
    )
    assert resp_whitespace.status_code in (400, 422)

    # Excessively long message (> 2000 chars)
    resp_long = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "A" * 2005}
    )
    assert resp_long.status_code in (400, 422)

    # Invalid target_type
    resp_bad_type = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "Hello", "target_type": "invalid_type"}
    )
    assert resp_bad_type.status_code in (400, 422)


def test_sender_impersonation_prevention():
    """Client-supplied sender IDs that mismatch credentials are explicitly rejected."""
    trip_id = create_trip(owner_id="alice_owner")

    # Attacker authenticated as bob tries to post as alice
    bob_token = create_access_token(user_id="bob_attacker")
    # Even if bob were a member:
    update_trip_sharing(trip_id, members={"alice_owner": {"role": "owner"}, "bob_attacker": {"role": "editor"}})

    resp = client.post(
        f"/chat/{trip_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={
            "content": "I am Alice giving everyone free money!",
            "sender_id": "alice_owner",
        }
    )
    assert resp.status_code == 400
    assert "impersonation" in resp.json()["detail"].lower()


def test_message_ownership_editing_and_deletion():
    """Users can only edit their own messages. Only sender or owner can delete."""
    trip_id = create_trip(owner_id="alice_owner")
    update_trip_sharing(
        trip_id,
        members={
            "alice_owner": {"role": "owner"},
            "bob_member": {"role": "editor"},
            "carol_member": {"role": "viewer"},
        }
    )

    # Bob posts a message
    resp_post = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "bob_member"},
        json={"content": "Original message by Bob"}
    )
    assert resp_post.status_code == 201
    msg_id = resp_post.json()["id"]

    # 1. Carol attempts to edit Bob's message -> 403 Forbidden
    resp_carol_edit = client.put(
        f"/chat/message/{msg_id}",
        headers={"X-User-ID": "carol_member"},
        json={"content": "Carol forged Bob's text"}
    )
    assert resp_carol_edit.status_code == 403

    # 2. Bob edits his own message -> 200 OK
    resp_bob_edit = client.put(
        f"/chat/message/{msg_id}",
        headers={"X-User-ID": "bob_member"},
        json={"content": "Updated message by Bob"}
    )
    assert resp_bob_edit.status_code == 200
    assert resp_bob_edit.json()["content"] == "Updated message by Bob"
    assert resp_bob_edit.json()["is_edited"] is True
    assert resp_bob_edit.json()["updated_at"] is not None

    # 3. Carol attempts to delete Bob's message -> 403 Forbidden
    resp_carol_del = client.delete(
        f"/chat/message/{msg_id}",
        headers={"X-User-ID": "carol_member"}
    )
    assert resp_carol_del.status_code == 403

    # 4. Trip Owner (Alice) moderates and deletes Bob's message -> 200 OK
    resp_owner_del = client.delete(
        f"/chat/message/{msg_id}",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_owner_del.status_code == 200
    assert resp_owner_del.json()["deleted"] is True

    # 5. Message is now not visible in standard list
    resp_list = client.get(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "bob_member"}
    )
    assert resp_list.status_code == 200
    assert resp_list.json()["total"] == 0


def test_attraction_specific_comments_isolation():
    """Comments on specific attractions are isolated and retrieved by target_id."""
    trip_id = create_trip(owner_id="alice_owner")

    # Post comment on Calangute Beach
    resp_c1 = client.post(
        f"/trip/{trip_id}/attractions/Calangute Beach/comments",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "Sunset is best here around 6 PM!"}
    )
    assert resp_c1.status_code == 201
    assert resp_c1.json()["target_type"] == "attraction"
    assert resp_c1.json()["target_id"] == "Calangute Beach"

    # Post comment on Fort Aguada
    resp_c2 = client.post(
        f"/trip/{trip_id}/attractions/Fort Aguada/comments",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "Wear comfortable shoes for the walk."}
    )
    assert resp_c2.status_code == 201
    assert resp_c2.json()["target_id"] == "Fort Aguada"

    # Fetch Calangute Beach comments
    resp_cal = client.get(
        f"/trip/{trip_id}/attractions/Calangute Beach/comments",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_cal.status_code == 200
    assert resp_cal.json()["total"] == 1
    assert resp_cal.json()["messages"][0]["content"] == "Sunset is best here around 6 PM!"

    # Fetch Fort Aguada comments
    resp_fort = client.get(
        f"/trip/{trip_id}/attractions/Fort Aguada/comments",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_fort.status_code == 200
    assert resp_fort.json()["total"] == 1
    assert resp_fort.json()["messages"][0]["content"] == "Wear comfortable shoes for the walk."

    # General chat query with target_type=trip returns 0
    resp_gen = client.get(
        f"/chat/{trip_id}?target_type=trip",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_gen.status_code == 200
    assert resp_gen.json()["total"] == 0


def test_pagination():
    """Limit and offset pagination works correctly."""
    trip_id = create_trip(owner_id="alice_owner")

    for i in range(12):
        client.post(
            f"/chat/{trip_id}",
            headers={"X-User-ID": "alice_owner"},
            json={"content": f"Message number {i + 1}"}
        )

    # Page 1: limit 5, offset 0
    p1 = client.get(f"/chat/{trip_id}?limit=5&offset=0", headers={"X-User-ID": "alice_owner"}).json()
    assert p1["total"] == 12
    assert len(p1["messages"]) == 5
    assert p1["has_more"] is True
    assert p1["messages"][0]["content"] == "Message number 1"

    # Page 3: limit 5, offset 10
    p3 = client.get(f"/chat/{trip_id}?limit=5&offset=10", headers={"X-User-ID": "alice_owner"}).json()
    assert len(p3["messages"]) == 2
    assert p3["has_more"] is False
    assert p3["messages"][1]["content"] == "Message number 12"


def test_concurrent_writes_without_losing_messages():
    """Multi-threaded concurrent writes to SQLite chat store lose zero messages."""
    trip_id = create_trip(owner_id="alice_owner")
    num_messages = 30

    def post_worker(idx):
        user = f"traveler_{idx % 5}"
        # Use direct client with verified token
        token = create_access_token(user_id=user)
        # Note: make them members
        resp = client.post(
            f"/chat/{trip_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": f"Concurrent message #{idx} from {user}"}
        )
        return resp.status_code

    # Add all 5 travelers as members
    update_trip_sharing(
        trip_id,
        members={
            "alice_owner": {"role": "owner"},
            **{f"traveler_{i}": {"role": "viewer"} for i in range(5)}
        }
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        status_codes = list(executor.map(post_worker, range(num_messages)))

    assert all(code == 201 for code in status_codes), f"Some writes failed: {status_codes}"

    # Verify all messages exist in store
    resp = client.get(f"/chat/{trip_id}?limit=100", headers={"X-User-ID": "alice_owner"})
    assert resp.status_code == 200
    assert resp.json()["total"] == num_messages
    assert len(resp.json()["messages"]) == num_messages
