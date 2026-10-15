import io
import os
import sys
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, update_trip_sharing
from backend.services.storage.memory_store import clear_trip_memories, create_entry, save_memory_photo
from backend.services.auth.jwt_service import create_access_token
from backend.services.auth.authorization import _sanitize_user_id
from PIL import Image as PILImage
import pypdf


def make_real_image_bytes(color="blue", fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    img = PILImage.new("RGB", (40, 40), color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return " ".join(page.extract_text() or "" for page in reader.pages)


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
    "source": "Kyoto",
    "destination": "Tokyo",
    "days": 3,
    "budget": {"total_budget": 80000, "estimated_cost": 50000},
    "travelers": [{"name": "Alice"}, {"name": "Bob"}],
    "places": [
        {"name": "Fushimi Inari", "category": "Shrine"},
        {"name": "Shibuya Crossing", "category": "Cityscape"},
    ],
}


def setup_test_trip(owner_id="alice_owner", member_id="bob_member"):
    payload = {
        "trip": dict(SAMPLE_TRIP),
        "dashboard": {"destination": "Tokyo", "days": 3},
        "summary": {"days": 3},
    }
    trip_id = save_trip(payload, owner_id=owner_id)
    update_trip_sharing(trip_id, members={owner_id: {"role": "owner"}, member_id: {"role": "editor"}})
    clear_trip_memories(trip_id)
    return trip_id


def test_album_authorization_and_isolation():
    """Unauthenticated users and strangers cannot access the memory album."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Unauthenticated -> 401
    resp_unauth = client.get(
        f"/trip/{trip_id}/memories/album",
        headers={"_raw_unauthenticated": "true"},
    )
    assert resp_unauth.status_code == 401

    # 2. Stranger -> 403
    resp_stranger = client.get(
        f"/trip/{trip_id}/memories/album",
        headers={"X-User-ID": "eve_stranger"},
    )
    assert resp_stranger.status_code == 403

    # 3. Non-existent trip -> 404
    resp_missing = client.get(
        "/trip/missing-trip-id/memories/album",
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp_missing.status_code == 404


def test_album_privacy_filtering():
    """Private photos in the album are visible strictly to their author."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Alice creates a private memory with photo
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"\x00" * 100)
    photo_fn_alice, photo_url_alice, _ = save_memory_photo(valid_jpeg, "alice.jpg", "image/jpeg", trip_id)
    create_entry(
        trip_id=trip_id,
        author_id="alice_owner",
        title="Alice Secret Photo",
        content="Alice private snapshot",
        photo_url=photo_url_alice,
        photo_filename=photo_fn_alice,
        is_private=True,
    )

    # 2. Bob creates a shared memory with photo
    photo_fn_bob1, photo_url_bob1, _ = save_memory_photo(valid_jpeg, "bob1.jpg", "image/jpeg", trip_id)
    create_entry(
        trip_id=trip_id,
        author_id="bob_member",
        title="Bob Shared Photo",
        content="Group photo at Shibuya",
        photo_url=photo_url_bob1,
        photo_filename=photo_fn_bob1,
        is_private=False,
    )

    # 3. Bob creates a private memory with photo
    photo_fn_bob2, photo_url_bob2, _ = save_memory_photo(valid_jpeg, "bob2.jpg", "image/jpeg", trip_id)
    create_entry(
        trip_id=trip_id,
        author_id="bob_member",
        title="Bob Secret Photo",
        content="Bob solo secret diary photo",
        photo_url=photo_url_bob2,
        photo_filename=photo_fn_bob2,
        is_private=True,
    )

    # Alice views album: sees her private photo + Bob's shared photo (total 2), but NOT Bob's private photo
    alice_album = client.get(
        f"/trip/{trip_id}/memories/album",
        headers={"X-User-ID": "alice_owner"},
    ).json()
    assert alice_album["total"] == 2
    alice_titles = [item["title"] for item in alice_album["items"]]
    assert "Alice Secret Photo" in alice_titles
    assert "Bob Shared Photo" in alice_titles
    assert "Bob Secret Photo" not in alice_titles

    # Bob views album: sees his private photo + his shared photo (total 2), but NOT Alice's private photo
    bob_album = client.get(
        f"/trip/{trip_id}/memories/album",
        headers={"X-User-ID": "bob_member"},
    ).json()
    assert bob_album["total"] == 2
    bob_titles = [item["title"] for item in bob_album["items"]]
    assert "Bob Secret Photo" in bob_titles
    assert "Bob Shared Photo" in bob_titles
    assert "Alice Secret Photo" not in bob_titles


def test_album_day_filtering_and_pagination():
    """Memory album correctly filters by day number and paginates."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + (b"\x00" * 50)

    # Create 3 photos for Day 1 and 2 photos for Day 2
    for i in range(3):
        fn, url, _ = save_memory_photo(valid_jpeg, f"day1_{i}.jpg", "image/jpeg", trip_id)
        create_entry(
            trip_id=trip_id,
            author_id="alice_owner",
            title=f"Day 1 Photo {i}",
            content="Day 1 scenery",
            day_number=1,
            photo_url=url,
            photo_filename=fn,
            is_private=False,
        )

    for i in range(2):
        fn, url, _ = save_memory_photo(valid_jpeg, f"day2_{i}.jpg", "image/jpeg", trip_id)
        create_entry(
            trip_id=trip_id,
            author_id="alice_owner",
            title=f"Day 2 Photo {i}",
            content="Day 2 scenery",
            day_number=2,
            photo_url=url,
            photo_filename=fn,
            is_private=False,
        )

    # Day 1 filter
    day1_resp = client.get(
        f"/trip/{trip_id}/memories/album?day_number=1",
        headers={"X-User-ID": "alice_owner"},
    ).json()
    assert day1_resp["total"] == 3
    assert len(day1_resp["items"]) == 3
    assert all(item["day_number"] == 1 for item in day1_resp["items"])

    # Pagination: limit 2, offset 0
    p1 = client.get(
        f"/trip/{trip_id}/memories/album?limit=2&offset=0",
        headers={"X-User-ID": "alice_owner"},
    ).json()
    assert p1["total"] == 5
    assert len(p1["items"]) == 2
    assert p1["has_more"] is True


def test_pdf_export_authorization_and_privacy():
    """PDF export endpoint enforces authentication and strict privacy rules."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    # 1. Unauthenticated -> 401
    resp_unauth = client.get(
        f"/trip/{trip_id}/journal/pdf",
        headers={"_raw_unauthenticated": "true"},
    )
    assert resp_unauth.status_code == 401

    # 2. Stranger -> 403
    resp_stranger = client.get(
        f"/trip/{trip_id}/journal/pdf",
        headers={"X-User-ID": "eve_stranger"},
    )
    assert resp_stranger.status_code == 403

    # 3. Create private entry for Alice and private entry for Bob
    create_entry(
        trip_id=trip_id,
        author_id="alice_owner",
        title="ALICE_SECRET_CODE_987",
        content="Confidential reflections only for Alice.",
        is_private=True,
    )
    create_entry(
        trip_id=trip_id,
        author_id="bob_member",
        title="BOB_SECRET_CODE_123",
        content="Confidential reflections only for Bob.",
        is_private=True,
    )
    create_entry(
        trip_id=trip_id,
        author_id="alice_owner",
        title="SHARED_GROUP_HIGHLIGHT",
        content="Everyone had a great dinner together.",
        is_private=False,
    )

    # Alice exports PDF
    alice_pdf = client.get(
        f"/trip/{trip_id}/journal/pdf",
        headers={"X-User-ID": "alice_owner"},
    )
    assert alice_pdf.status_code == 200
    assert alice_pdf.headers["content-type"] == "application/pdf"
    assert alice_pdf.content.startswith(b"%PDF-")
    alice_text = extract_pdf_text(alice_pdf.content)
    # Alice's PDF contains her secret and the shared highlight, but NOT Bob's secret
    assert "ALICE_SECRET_CODE_987" in alice_text
    assert "SHARED_GROUP_HIGHLIGHT" in alice_text
    assert "BOB_SECRET_CODE_123" not in alice_text

    # Bob exports PDF
    bob_pdf = client.get(
        f"/trip/{trip_id}/journal/pdf",
        headers={"X-User-ID": "bob_member"},
    )
    assert bob_pdf.status_code == 200
    assert bob_pdf.content.startswith(b"%PDF-")
    bob_text = extract_pdf_text(bob_pdf.content)
    # Bob's PDF contains his secret and shared highlight, but NOT Alice's secret
    assert "BOB_SECRET_CODE_123" in bob_text
    assert "SHARED_GROUP_HIGHLIGHT" in bob_text
    assert "ALICE_SECRET_CODE_987" not in bob_text


def test_pdf_export_photo_embedding_and_traversal_protection():
    """PDF generator validates photos, embeds safe photos, and rejects path traversal."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    valid_jpeg = make_real_image_bytes(color="green", fmt="JPEG")
    safe_fn, photo_url, _ = save_memory_photo(valid_jpeg, "test_pic.jpg", "image/jpeg", trip_id)

    # Valid entry with genuine photo
    create_entry(
        trip_id=trip_id,
        author_id="alice_owner",
        title="Photo Memory Entry",
        content="Beautiful mountain photo.",
        photo_url=photo_url,
        photo_filename=safe_fn,
        is_private=False,
    )

    # Malicious entry attempting path traversal to read system files
    create_entry(
        trip_id=trip_id,
        author_id="alice_owner",
        title="Traversal Attempt",
        content="Attempting to embed sensitive local file.",
        photo_filename="../../etc/passwd",
        is_private=False,
    )

    # Export PDF should succeed gracefully without crashing and without reading arbitrary files
    resp = client.get(
        f"/trip/{trip_id}/journal/pdf",
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")
    pdf_text = extract_pdf_text(resp.content)
    assert "Photo Memory Entry" in pdf_text
    assert "Traversal Attempt" in pdf_text


def test_pdf_export_unicode_and_large_content():
    """PDF generation handles Unicode text, long entries, and missing photos cleanly."""
    trip_id = setup_test_trip(owner_id="alice_owner", member_id="bob_member")

    long_text = "Exploring Tokyo was fantastic! " * 50
    unicode_title = "Café & Sanctuary • 東京 • Счастливый день"
    unicode_content = f"{long_text}\nVisited amazing temples with matcha café & souvenir shops."

    create_entry(
        trip_id=trip_id,
        author_id="alice_owner",
        title=unicode_title,
        content=unicode_content,
        day_number=1,
        attraction_name="Fushimi Inari Taisha",
        is_private=False,
    )

    resp = client.get(
        f"/trip/{trip_id}/journal/pdf",
        headers={"X-User-ID": "alice_owner"},
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF-")
    assert len(resp.content) > 1000  # Non-trivial PDF generated
