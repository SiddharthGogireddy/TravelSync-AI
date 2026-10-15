import concurrent.futures
import os
import sys
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, update_trip_sharing
from backend.services.storage.activity_store import clear_trip_activity, clear_user_notifications
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


def test_activity_membership_isolation():
    """Unauthenticated users and strangers cannot read trip activity."""
    trip_id = create_trip(owner_id="alice_owner")

    # 1. Unauthenticated -> 401
    resp_unauth = client.get(
        f"/trip/{trip_id}/activity",
        headers={"_raw_unauthenticated": "true"}
    )
    assert resp_unauth.status_code == 401

    # 2. Stranger -> 403
    resp_stranger = client.get(
        f"/trip/{trip_id}/activity",
        headers={"X-User-ID": "charlie_stranger"}
    )
    assert resp_stranger.status_code == 403

    # 3. Owner -> 200
    resp_owner = client.get(
        f"/trip/{trip_id}/activity",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_owner.status_code == 200
    assert "activities" in resp_owner.json()


def test_notifications_authentication_required():
    """Unauthenticated users cannot read notifications."""
    resp = client.get("/notifications", headers={"_raw_unauthenticated": "true"})
    assert resp.status_code == 401


def test_event_recording_and_notification_fanout():
    """Posting chat messages, comments, and votes creates activity and notifies other members."""
    trip_id = create_trip(owner_id="alice_owner")
    clear_trip_activity(trip_id)

    # Add bob as viewer
    update_trip_sharing(
        trip_id,
        members={
            "alice_owner": {"role": "owner"},
            "bob_viewer": {"role": "viewer"},
        }
    )

    # 1. Alice posts a chat message
    resp_chat = client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "Welcome to our Goa trip chat!"}
    )
    assert resp_chat.status_code == 201

    # Verify activity exists in trip feed
    resp_feed = client.get(
        f"/trip/{trip_id}/activity",
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_feed.status_code == 200
    activities = resp_feed.json()["activities"]
    assert len(activities) >= 1
    assert activities[0]["event_type"] == "chat_message_posted"
    assert "Welcome to our Goa trip chat!" not in activities[0]["summary"]  # body is not dumped in summary

    # Verify Bob received an in-app notification
    resp_bob_notifs = client.get(
        "/notifications",
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_bob_notifs.status_code == 200
    bob_notifs = resp_bob_notifs.json()["notifications"]
    assert len(bob_notifs) >= 1
    assert bob_notifs[0]["is_read"] is False
    assert bob_notifs[0]["trip_id"] == trip_id

    # Verify Alice (the actor) did NOT receive a notification for her own message
    resp_alice_notifs = client.get(
        f"/notifications?trip_id={trip_id}",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_alice_notifs.status_code == 200
    assert resp_alice_notifs.json()["total"] == 0

    # 2. Bob casts a group vote on Fort Aguada
    resp_vote = client.post(
        f"/trip/{trip_id}/group-vote",
        headers={"X-User-ID": "bob_viewer"},
        json={"traveler_name": "Bob", "attraction_name": "Fort Aguada", "vote": "up"}
    )
    assert resp_vote.status_code == 200

    # Verify Alice now receives a notification about Bob's vote
    resp_alice_after_vote = client.get(
        f"/notifications?trip_id={trip_id}",
        headers={"X-User-ID": "alice_owner"}
    )
    assert resp_alice_after_vote.status_code == 200
    alice_notifs = resp_alice_after_vote.json()["notifications"]
    assert len(alice_notifs) == 1
    assert "Fort Aguada" in alice_notifs[0]["title"] or "Fort Aguada" in alice_notifs[0]["message"]


def test_notification_ownership_and_marking_read():
    """Users can only mark their own notifications as read. Mark-all works properly."""
    trip_id = create_trip(owner_id="alice_owner")
    clear_trip_activity(trip_id)
    clear_user_notifications("bob_viewer")
    clear_user_notifications("carol_viewer")

    update_trip_sharing(
        trip_id,
        members={
            "alice_owner": {"role": "owner"},
            "bob_viewer": {"role": "viewer"},
            "carol_viewer": {"role": "viewer"},
        }
    )

    # Alice posts a comment to generate notifications for Bob and Carol
    client.post(
        f"/trip/{trip_id}/attractions/Calangute Beach/comments",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "Check out the beach shacks!"}
    )

    bob_notifs = client.get("/notifications", headers={"X-User-ID": "bob_viewer"}).json()["notifications"]
    assert len(bob_notifs) >= 1
    bob_notif_id = bob_notifs[0]["id"]

    # 1. Carol tries to mark Bob's notification as read -> 403 Forbidden
    resp_carol_steal = client.patch(
        f"/notifications/{bob_notif_id}/read",
        headers={"X-User-ID": "carol_viewer"}
    )
    assert resp_carol_steal.status_code == 403

    # 2. Bob marks his own notification as read -> 200 OK
    resp_bob_mark = client.patch(
        f"/notifications/{bob_notif_id}/read",
        headers={"X-User-ID": "bob_viewer"}
    )
    assert resp_bob_mark.status_code == 200
    assert resp_bob_mark.json()["success"] is True

    # Check unread count for Bob is now 0
    unread_res = client.get("/notifications/unread-count", headers={"X-User-ID": "bob_viewer"}).json()
    assert unread_res["unread_count"] == 0

    # 3. Post another action to test mark-all-read
    client.post(
        f"/chat/{trip_id}",
        headers={"X-User-ID": "alice_owner"},
        json={"content": "Don't forget sunscreen!"}
    )
    assert client.get("/notifications/unread-count", headers={"X-User-ID": "bob_viewer"}).json()["unread_count"] == 1

    # Bob marks all read
    resp_mark_all = client.post("/notifications/mark-all-read", headers={"X-User-ID": "bob_viewer"})
    assert resp_mark_all.status_code == 200
    assert resp_mark_all.json()["affected"] >= 1
    assert client.get("/notifications/unread-count", headers={"X-User-ID": "bob_viewer"}).json()["unread_count"] == 0


def test_activity_deduplication():
    """Rapid duplicate submissions are safely deduplicated to prevent notification spam."""
    from backend.services.storage.activity_store import record_activity
    trip_id = create_trip(owner_id="alice_owner")
    clear_trip_activity(trip_id)

    # First event recorded
    e1 = record_activity(
        trip_id=trip_id,
        actor_id="alice_owner",
        event_type="test_event",
        title="Test Action",
        summary="Testing deduplication",
        target_id="item_1",
    )
    assert e1.get("duplicate") is not True

    # Immediate duplicate event within 5s is marked duplicate and suppressed
    e2 = record_activity(
        trip_id=trip_id,
        actor_id="alice_owner",
        event_type="test_event",
        title="Test Action",
        summary="Testing deduplication",
        target_id="item_1",
    )
    assert e2.get("duplicate") is True


def test_concurrent_activity_and_notifications():
    """Concurrent activity writes across worker threads execute safely without losing events."""
    trip_id = create_trip(owner_id="alice_owner")
    clear_trip_activity(trip_id)

    num_events = 20

    def event_worker(idx):
        from backend.services.storage.activity_store import record_activity
        res = record_activity(
            trip_id=trip_id,
            actor_id=f"worker_{idx % 4}",
            event_type="worker_step",
            title=f"Worker {idx}",
            summary=f"Worker summary {idx}",
            target_id=f"target_{idx}",
            notify_members=False,
        )
        return res["id"] is not None

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(event_worker, range(num_events)))

    assert all(results)
    feed = client.get(f"/trip/{trip_id}/activity?limit=100", headers={"X-User-ID": "alice_owner"}).json()
    assert feed["total"] == num_events
