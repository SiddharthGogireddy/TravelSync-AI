import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip
from backend.services.external.place_detail_service import (
    get_place_details,
    _is_valid_http_url,
    _PLACE_DETAILS_CACHE,
)

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BASE_DIR / "frontend" / "src"


@pytest.fixture(autouse=True)
def clear_place_cache():
    _PLACE_DETAILS_CACHE.clear()
    yield
    _PLACE_DETAILS_CACHE.clear()


def test_attraction_details_with_practical_visitor_info():
    """Verify attraction details contain visitor info and DO NOT include hotel-specific fields."""
    mock_wiki = {
        "description": "Historical monument built in 1591.",
        "image_url": "https://upload.wikimedia.org/charminar.jpg",
        "image_source": "Wikimedia Commons",
        "website_url": "https://en.wikipedia.org/wiki/Charminar",
        "lat": 17.3616,
        "lon": 78.4747,
    }

    with patch("backend.services.external.place_detail_service.fetch_wikipedia_details", new=AsyncMock(return_value=mock_wiki)):
        res = client.get("/places/details?name=Charminar&place_type=attraction&category=Monument&lat=17.3616&lon=78.4747")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["success"] is True
        details = data["details"]

        assert details["name"] == "Charminar"
        assert details["place_type"] == "attraction"
        assert details["category"] == "Monument"
        assert details["image_url"] == "https://upload.wikimedia.org/charminar.jpg"
        assert details["image_source"] == "Wikimedia Commons"
        assert details["website_url"] == "https://en.wikipedia.org/wiki/Charminar"

        # Practical visitor info present for attraction
        assert "opening_hours" in details
        assert details["opening_hours"]["opens"] is not None
        assert details["estimated_visit_duration"] is not None
        assert details["entry_fee"] is not None
        assert details["best_time_to_visit"] is not None

        # Hotel-specific fields MUST NOT be populated for ordinary attractions
        assert details.get("star_rating") is None
        assert details.get("check_in_time") is None
        assert details.get("check_out_time") is None
        assert details.get("amenities") is None


def test_hotel_specific_fields():
    """Verify hotel place details contain lodging-specific fields and omit irrelevant attraction timings."""
    res = client.get("/places/details?name=Taj%20Falaknuma&place_type=hotel&category=Hotel&lat=17.331&lon=78.467")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    details = data["details"]

    assert details["name"] == "Taj Falaknuma"
    assert details["place_type"] == "hotel"
    assert details["star_rating"] == "Hospitality Accommodation"
    assert details["price_per_night"] is not None
    assert "amenities" in details and len(details["amenities"]) > 0
    assert details["check_in_time"] == "02:00 PM (Standard)"
    assert details["check_out_time"] == "11:00 AM (Standard)"

    # Should NOT have attraction closed days
    assert details.get("closed_days") is None


def test_missing_photos_and_fallback_placeholder():
    """Verify when no external image is found, endpoint cleanly returns None without crashing."""
    with patch("backend.services.external.place_detail_service.fetch_wikipedia_details", new=AsyncMock(return_value={})):
        with patch("backend.services.external.place_detail_service.fetch_opentripmap_details", new=AsyncMock(return_value={})):
            res = client.get("/places/details?name=Unknown%20Site&place_type=attraction")
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            details = data["details"]
            assert details["image_url"] is None
            assert details["image_source"] is None
            assert "description" in details and details["description"] is not None


def test_missing_ratings_and_review_counts_never_fabricated():
    """Verify missing ratings are None and never fabricated with fake numbers."""
    with patch("backend.services.external.place_detail_service.fetch_wikipedia_details", new=AsyncMock(return_value={})):
        with patch("backend.services.external.place_detail_service.fetch_opentripmap_details", new=AsyncMock(return_value={})):
            res = client.get("/places/details?name=Silent%20Spot&place_type=attraction")
            assert res.status_code == 200
            details = res.json()["details"]
            assert details["provider_rating"] is None
            assert details["provider_rating_source"] is None
            assert details["provider_reviews_count"] is None


def test_invalid_or_non_http_image_urls_discarded():
    """Verify non-HTTP URLs are safely rejected."""
    assert not _is_valid_http_url("javascript:alert(1)")
    assert not _is_valid_http_url("ftp://example.com/pic.jpg")
    assert not _is_valid_http_url("data:image/png;base64,...")
    assert _is_valid_http_url("https://example.com/pic.jpg")
    assert _is_valid_http_url("http://example.com/pic.png")

    bad_mock = {
        "image_url": "javascript:malicious()",
        "description": "Safe text",
    }
    with patch("backend.services.external.place_detail_service.fetch_wikipedia_details", new=AsyncMock(return_value=bad_mock)):
        res = client.get("/places/details?name=BadURLPlace")
        assert res.status_code == 200
        assert res.json()["details"]["image_url"] is None


def test_external_service_failures_and_timeouts():
    """Verify endpoint gracefully handles external network timeouts and errors."""
    import httpx
    with patch("backend.services.external.place_detail_service.fetch_wikipedia_details", side_effect=httpx.TimeoutException("Timeout")):
        with patch("backend.services.external.place_detail_service.fetch_opentripmap_details", side_effect=httpx.ConnectError("Conn error")):
            res = client.get("/places/details?name=TimeoutLandmark&lat=12.0&lon=77.0")
            assert res.status_code == 200
            details = res.json()["details"]
            assert details["name"] == "TimeoutLandmark"
            assert details["description"] is not None


def test_caching_avoids_redundant_external_requests():
    """Verify in-memory caching serves repeated requests without calling external APIs."""
    call_count = 0

    async def mock_fetch(name):
        nonlocal call_count
        call_count += 1
        return {"description": "Cached extract", "image_url": "https://img.com/1.jpg", "image_source": "Wiki"}

    with patch("backend.services.external.place_detail_service.fetch_wikipedia_details", side_effect=mock_fetch):
        res1 = client.get("/places/details?name=CachedSpot")
        res2 = client.get("/places/details?name=CachedSpot")
        assert res1.status_code == 200
        assert res2.status_code == 200
        assert call_count == 1  # Called only once due to cache


def test_viewing_details_leaves_trip_intact_and_preserves_remove_replace():
    """Verify viewing details does not mutate trip state, and Remove/Replace work seamlessly."""
    raw_trip = {
        "trip": {
            "destination": "Goa",
            "source": "Bengaluru",
            "days": 1,
            "day_schedule": {
                "1": [
                    {"name": "Calangute Beach", "category": "Beach", "lat": 15.543, "lon": 73.755},
                    {"name": "Fort Aguada", "category": "Fort", "lat": 15.492, "lon": 73.773},
                ]
            },
            "places": [
                {"name": "Calangute Beach", "category": "Beach", "lat": 15.543, "lon": 73.755},
                {"name": "Fort Aguada", "category": "Fort", "lat": 15.492, "lon": 73.773},
            ],
            "hotels": [
                {"name": "Taj Fort Aguada Resort", "lat": 15.495, "lon": 73.775, "distance_km": 1.2}
            ],
            "excluded_places": [],
        }
    }
    trip_id = save_trip(raw_trip)

    # 1. View details for Calangute Beach
    det_res = client.get(f"/places/details?name=Calangute%20Beach&place_type=attraction&lat=15.543&lon=73.755")
    assert det_res.status_code == 200

    # 2. View details for hotel
    hotel_res = client.get(f"/places/details?name=Taj%20Fort%20Aguada%20Resort&place_type=hotel&lat=15.495&lon=73.775")
    assert hotel_res.status_code == 200

    # 3. Verify saved trip in storage remains completely unchanged
    reloaded = load_trip(trip_id)
    inner = reloaded.get("trip", reloaded)
    assert len(inner["day_schedule"]["1"]) == 2
    assert inner["day_schedule"]["1"][0]["name"] == "Calangute Beach"
    assert inner["hotels"][0]["name"] == "Taj Fort Aguada Resort"

    # 4. Remove action still functions
    rem_res = client.post(f"/trip/{trip_id}/attraction-action", json={
        "day": "1",
        "attraction_name": "Calangute Beach",
        "action": "remove",
    })
    assert rem_res.status_code == 200
    assert len(rem_res.json()["trip"]["day_schedule"]["1"]) == 1
    assert rem_res.json()["trip"]["day_schedule"]["1"][0]["name"] == "Fort Aguada"


# ============================================================================
# FRONTEND SOURCE CODE & COMPONENT STRUCTURE VERIFICATION
# ============================================================================

def test_frontend_place_detail_modal_component():
    """Verify PlaceDetailModal.tsx implements accessible dialog, Escape listener, and sections."""
    modal_file = FRONTEND_SRC / "components" / "PlaceDetailModal.tsx"
    assert modal_file.exists(), "PlaceDetailModal.tsx must exist"
    content = modal_file.read_text(encoding="utf-8")

    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content
    assert 'aria-labelledby="place-detail-title"' in content
    assert 'onClose' in content
    assert 'Escape' in content
    assert 'Practical Visitor Information' in content
    assert 'Hotel & Lodging Details' in content
    assert 'isHotel' in content
    assert 'Google Maps' in content
    assert 'Public Provider Rating' in content
    assert 'TravelSync Match Score' in content


def test_frontend_day_card_integrates_info_button():
    """Verify DayCard.tsx includes accessible info buttons and preserves Remove/Replace."""
    day_card_file = FRONTEND_SRC / "components" / "DayCard.tsx"
    content = day_card_file.read_text(encoding="utf-8")

    assert "onShowPlaceInfo" in content
    assert "place-info-btn" in content
    assert "View details for" in content
    assert "aria-label=" in content
    assert "attraction-replace-btn" in content
    assert "attraction-remove-btn" in content


def test_frontend_trip_view_integrates_place_details():
    """Verify TripView.tsx renders PlaceDetailModal and hotel details buttons."""
    trip_view_file = FRONTEND_SRC / "pages" / "TripView.tsx"
    content = trip_view_file.read_text(encoding="utf-8")

    assert "PlaceDetailModal" in content
    assert "getPlaceDetails" in content
    assert "placeDetailModal" in content
    assert "handleShowPlaceInfo" in content
    assert "hotel-info-btn" in content
    assert "Recommended Accommodations" in content
