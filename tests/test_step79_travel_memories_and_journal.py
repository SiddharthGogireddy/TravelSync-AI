import concurrent.futures
import io
import os
import sys
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, update_trip_sharing
from backend.services.storage.memory_store import clear_trip_memories
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
    "source": "Paris",
    "destination": "Nice",
    "days": 4,
    "budget": {"total_budget": 50000, "estimated_cost": 30000},
    "travelers": [{"name": "Alice"}, {"name": "Bob"}],
    "day_schedule": {
        "1": [{"name": "Promenade des Anglais", "category": "Walk"}],
        "2": [{"name": "Castle Hill", "category": "Viewpoint"}],
    },
    "places": [
        {"name": "Promenade des Anglais", "category": "Walk"},
        {"name": "Castle Hill", "category": "Viewpoint"},
    ],
}


def setup_test_trip(owner_id="alice_owner", member_id="bob_member"):
    payload = {
        "trip": dict(SAMPLE_TRIP),
        "dashboard": {"destination": "Nice", "days": 4},
        "summary": {"days": 4},
    }
    trip_id = save_trip(payload, owner_id=owner_id)
    # Add bob_member as editor
    update_trip_sharing(trip_id, members={owner_id: {"role": "owner"}, member_id: {"role": "editor"}})
    clear_trip_memories(trip_id)
    clear_trip_activity(trip_id)
    clear_user_notifications(owner_id)
    clear_user_notifications(member_id)
    return trip_id


def test_journal_authentication_and_isolation():
    """Unauthenticated users and strangers cannot read or write memories."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Unauthenticated request (no JWT token) -> 401
    resp_unauth = client.get(
        f"/trip/{trip_id}/journal",
        headers={"_raw_unauthenticated": "true"},
    )
    assert resp_unauth.status_code == 401

    # 2. Stranger request (not on trip) -> 403
    resp_stranger = client.get(
        f"/trip/{trip_id}/journal",
        headers={"X-User-ID": "eve_stranger"},
    )
    assert resp_stranger.status_code == 403

    # 3. Post as stranger -> 403
    resp_stranger_post = client.post(
        f"/trip/{trip_id}/journal",
        json={"content": "Sneaking into trip journal"},
        headers={"X-User-ID": "eve_stranger"},
    )
    assert resp_stranger_post.status_code == 403

    # 4. Non-existent trip -> 404
    resp_missing = client.get(
        "/trip/non-existent-trip-id/journal",
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp_missing.status_code == 404


def test_journal_crud_and_ownership():
    """Author can create, view, and edit; strangers/non-authors cannot edit; author & owner can delete."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Alice creates a shared memory
    create_resp = client.post(
        f"/trip/{trip_id}/journal",
        json={
            "title": "Sunset at Promenade",
            "content": "The sunset over the Mediterranean was breathtaking today!",
            "day_number": 1,
            "attraction_name": "Promenade des Anglais",
            "is_private": False,
        },
        headers={"X-User-ID": "alice_owner"},
    )
    assert create_resp.status_code == 201
    entry = create_resp.json()
    assert entry["id"]
    assert entry["title"] == "Sunset at Promenade"
    assert entry["day_number"] == 1
    assert entry["attraction_name"] == "Promenade des Anglais"
    assert entry["author_id"] == "alice_owner"
    assert entry["is_private"] is False
    entry_id = entry["id"]

    # 2. Bob (member) cannot edit Alice's entry -> 403
    edit_bob_resp = client.put(
        f"/trip/{trip_id}/journal/{entry_id}",
        json={"title": "Hacked Title"},
        headers={"X-User-ID": "bob_member"},
    )
    assert edit_bob_resp.status_code == 403

    # 3. Alice edits her own entry -> 200
    edit_alice_resp = client.put(
        f"/trip/{trip_id}/journal/{entry_id}",
        json={"title": "Updated Sunset View", "content": "Updated reflections on the beach."},
        headers={"X-User-ID": "alice_owner"},
    )
    assert edit_alice_resp.status_code == 200
    assert edit_alice_resp.json()["title"] == "Updated Sunset View"
    assert edit_alice_resp.json()["content"] == "Updated reflections on the beach."

    # 4. Bob creates an entry
    bob_entry_resp = client.post(
        f"/trip/{trip_id}/journal",
        json={"content": "Bob's memory from Castle Hill", "day_number": 2},
        headers={"X-User-ID": "bob_member"},
    )
    assert bob_entry_resp.status_code == 201
    bob_entry_id = bob_entry_resp.json()["id"]

    # 5. Alice (trip owner) can delete Bob's entry (moderation)
    del_owner_resp = client.delete(
        f"/trip/{trip_id}/journal/{bob_entry_id}",
        headers={"X-User-ID": "alice_owner"},
    )
    assert del_owner_resp.status_code == 200
    assert del_owner_resp.json()["deleted"] is True

    # 6. Bob cannot delete Alice's entry -> 403
    del_bob_resp = client.delete(
        f"/trip/{trip_id}/journal/{entry_id}",
        headers={"X-User-ID": "bob_member"},
    )
    assert del_bob_resp.status_code == 403

    # 7. Alice deletes her own entry -> 200
    del_alice_resp = client.delete(
        f"/trip/{trip_id}/journal/{entry_id}",
        headers={"X-User-ID": "alice_owner"},
    )
    assert del_alice_resp.status_code == 200


def test_privacy_controls_and_isolation():
    """Private entries are only visible to the author, never to other trip members."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # Alice creates a private entry
    alice_priv = client.post(
        f"/trip/{trip_id}/journal",
        json={
            "title": "Alice's Secret Thoughts",
            "content": "This is totally private to Alice.",
            "is_private": True,
        },
        headers={"X-User-ID": "alice_owner"},
    )
    assert alice_priv.status_code == 201

    # Bob creates a shared entry
    bob_pub = client.post(
        f"/trip/{trip_id}/journal",
        json={
            "title": "Group Gelato Stop",
            "content": "Amazing pistachio gelato!",
            "is_private": False,
        },
        headers={"X-User-ID": "bob_member"},
    )
    assert bob_pub.status_code == 201

    # Bob creates a private entry
    bob_priv = client.post(
        f"/trip/{trip_id}/journal",
        json={
            "title": "Bob's Secret Journal",
            "content": "Secret notes from Bob.",
            "is_private": True,
        },
        headers={"X-User-ID": "bob_member"},
    )
    assert bob_priv.status_code == 201

    # Check Alice's view: sees her private entry + shared entry (total 2), but NOT Bob's private entry
    alice_list = client.get(
        f"/trip/{trip_id}/journal",
        headers={"X-User-ID": "alice_owner"},
    ).json()
    assert alice_list["total"] == 2
    alice_titles = [e["title"] for e in alice_list["entries"]]
    assert "Alice's Secret Thoughts" in alice_titles
    assert "Group Gelato Stop" in alice_titles
    assert "Bob's Secret Journal" not in alice_titles

    # Check Bob's view: sees his private entry + shared entry (total 2), but NOT Alice's private entry
    bob_list = client.get(
        f"/trip/{trip_id}/journal",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert bob_list["total"] == 2
    bob_titles = [e["title"] for e in bob_list["entries"]]
    assert "Bob's Secret Journal" in bob_titles
    assert "Group Gelato Stop" in bob_titles
    assert "Alice's Secret Thoughts" not in bob_titles


def test_activity_feed_privacy_integration():
    """Shared entries generate feed activities; private entries NEVER do, nor do they leak text."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Post a private entry
    client.post(
        f"/trip/{trip_id}/journal",
        json={
            "title": "Secret Alice Entry",
            "content": "Sensitive medical / personal notes.",
            "is_private": True,
        },
        headers={"X-User-ID": "alice_owner"},
    )

    # Activity feed should be empty because entry is private
    act_resp = client.get(
        f"/trip/{trip_id}/activity",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert act_resp["total"] == 0

    # 2. Post a shared entry
    client.post(
        f"/trip/{trip_id}/journal",
        json={
            "title": "Public Photo Time",
            "content": "A beautiful day in Nice with everyone!",
            "day_number": 2,
            "is_private": False,
        },
        headers={"X-User-ID": "alice_owner"},
    )

    # Activity feed should now have 1 event
    act_resp2 = client.get(
        f"/trip/{trip_id}/activity",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert act_resp2["total"] == 1
    event = act_resp2["activities"][0]
    assert event["event_type"] == "journal_entry_created"
    # Ensure raw journal content is NOT leaked in the summary
    assert "A beautiful day in Nice with everyone!" not in event["summary"]
    assert "Sensitive medical" not in event["summary"]


def test_photo_upload_validation_and_serving():
    """Validates photo uploads, file types, magic bytes, size limits, and path traversal protection."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Valid JPEG image (valid magic bytes \xff\xd8\xff)
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"\x00" * 100)
    upload_resp = client.post(
        f"/trip/{trip_id}/journal/upload-photo",
        files={"file": ("beach.jpg", io.BytesIO(valid_jpeg), "image/jpeg")},
        headers={"X-User-ID": "alice_owner"},
    )
    assert upload_resp.status_code == 200
    up_data = upload_resp.json()
    assert up_data["photo_url"].startswith(f"/trip/{trip_id}/journal/photos/")
    assert up_data["photo_filename"].endswith(".jpg")
    safe_filename = up_data["photo_filename"]

    # 2. Stream the uploaded photo back
    get_photo_resp = client.get(
        f"/trip/{trip_id}/journal/photos/{safe_filename}",
        headers={"X-User-ID": "bob_member"},
    )
    assert get_photo_resp.status_code == 200
    assert get_photo_resp.content == valid_jpeg
    assert get_photo_resp.headers.get("cache-control") == "private, max-age=86400"

    # 3. Path traversal attack attempt -> 404
    bad_traversal = client.get(
        f"/trip/{trip_id}/journal/photos/../../etc/passwd",
        headers={"X-User-ID": "bob_member"},
    )
    assert bad_traversal.status_code in (404, 400)

    # 4. Reject invalid extension (e.g. .py or .exe) -> 400
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
    resp_exe = client.post(
        f"/trip/{trip_id}/journal/upload-photo",
        files={"file": ("malware.exe", io.BytesIO(fake_exe), "application/octet-stream")},
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp_exe.status_code == 400

    # 5. Reject file with .png extension but spoofed magic bytes -> 400
    spoofed = b"This is not a real PNG image."
    resp_spoof = client.post(
        f"/trip/{trip_id}/journal/upload-photo",
        files={"file": ("fake.png", io.BytesIO(spoofed), "image/png")},
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp_spoof.status_code == 400
    assert "magic bytes mismatch" in resp_spoof.json()["detail"].lower()

    # 6. Reject file exceeding 5MB -> 413
    oversized = b"\xff\xd8\xff" + (b"A" * (5 * 1024 * 1024 + 100))
    resp_large = client.post(
        f"/trip/{trip_id}/journal/upload-photo",
        files={"file": ("huge.jpg", io.BytesIO(oversized), "image/jpeg")},
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp_large.status_code in (413, 400)


def test_pagination_and_day_filtering():
    """Tests day filtering, attraction filtering, and pagination limit/offset."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # Create 5 memories on different days
    for day in range(1, 6):
        client.post(
            f"/trip/{trip_id}/journal",
            json={
                "title": f"Memory Day {day}",
                "content": f"Exploring on Day {day}",
                "day_number": day,
                "attraction_name": "Castle Hill" if day == 2 else None,
                "is_private": False,
            },
            headers={"X-User-ID": "alice_owner"},
        )

    # Filter by day 2
    day2_resp = client.get(
        f"/trip/{trip_id}/journal?day_number=2",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert day2_resp["total"] == 1
    assert day2_resp["entries"][0]["title"] == "Memory Day 2"
    assert day2_resp["entries"][0]["attraction_name"] == "Castle Hill"

    # Pagination: limit 2, offset 0
    page1 = client.get(
        f"/trip/{trip_id}/journal?limit=2&offset=0",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert len(page1["entries"]) == 2
    assert page1["total"] == 5
    assert page1["has_more"] is True

    # Pagination: limit 2, offset 2
    page2 = client.get(
        f"/trip/{trip_id}/journal?limit=2&offset=2",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert len(page2["entries"]) == 2
    assert page2["has_more"] is True


def test_concurrent_journal_writes():
    """Concurrent writes do not lock up or corrupt SQLite database."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    def post_worker(idx):
        user = "alice_owner" if idx % 2 == 0 else "bob_member"
        res = client.post(
            f"/trip/{trip_id}/journal",
            json={
                "title": f"Concurrent Memory {idx}",
                "content": f"Concurrent thread content {idx}",
                "is_private": False,
            },
            headers={"X-User-ID": user},
        )
        return res.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        statuses = list(executor.map(post_worker, range(15)))

    assert all(s == 201 for s in statuses)

    final_list = client.get(
        f"/trip/{trip_id}/journal?limit=50",
        headers={"X-User-ID": "alice_owner"},
    ).json()
    assert final_list["total"] == 15
