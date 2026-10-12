import os
import sys
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)


def _build_test_trip(is_multi=False):
    """Helper to generate a rich test trip in memory."""
    if not is_multi:
        trip_data = {
            "trip": {
                "destination": "Hyderabad",
                "source": "Bengaluru",
                "days": 2,
                "travel_mode": "car",
                "travelers": [{"name": "Alice", "interests": ["History", "Architecture"], "budget": "Medium", "pace": "Balanced"}],
                "destination_location": {"lat": 17.385, "lon": 78.486},
                "hotels": [{"name": "Taj Falaknuma", "lat": 17.331, "lon": 78.467, "distance_km": 5.0}],
                "places": [
                    {"name": "Charminar", "category": "Monument", "lat": 17.3616, "lon": 78.4747, "score": 4.8},
                    {"name": "Golconda Fort", "category": "Fort", "lat": 17.3833, "lon": 78.4011, "score": 4.7},
                    {"name": "Chowmahalla Palace", "category": "Palace", "lat": 17.3578, "lon": 78.4717, "score": 4.6},
                    {"name": "Birla Mandir", "category": "Temple", "lat": 17.4062, "lon": 78.4691, "score": 4.5},
                    {"name": "Salar Jung Museum", "category": "Museum", "lat": 17.3713, "lon": 78.4804, "score": 4.6},
                    {"name": "Qutb Shahi Tombs", "category": "Heritage Monument", "lat": 17.3920, "lon": 78.4010, "score": 4.4, "description": "Historic royal necropolis"},
                    {"name": "Nehru Zoological Park", "category": "Zoo", "lat": 17.3510, "lon": 78.4500, "score": 4.2, "description": "Expansive wildlife reserve"},
                ],
                "day_schedule": {
                    "1": [
                        {"name": "Charminar", "category": "Monument", "lat": 17.3616, "lon": 78.4747, "score": 4.8, "travel_time_minutes": 0},
                        {"name": "Golconda Fort", "category": "Fort", "lat": 17.3833, "lon": 78.4011, "score": 4.7, "travel_time_minutes": 25},
                        {"name": "Chowmahalla Palace", "category": "Palace", "lat": 17.3578, "lon": 78.4717, "score": 4.6, "travel_time_minutes": 20},
                    ],
                    "2": [
                        {"name": "Birla Mandir", "category": "Temple", "lat": 17.4062, "lon": 78.4691, "score": 4.5, "travel_time_minutes": 0},
                        {"name": "Salar Jung Museum", "category": "Museum", "lat": 17.3713, "lon": 78.4804, "score": 4.6, "travel_time_minutes": 15},
                    ],
                },
                "budget": {"total_budget": 20000, "estimated_cost": 14000, "remaining": 6000},
                "excluded_places": [],
            }
        }
    else:
        trip_data = {
            "trip": {
                "destination": "Bengaluru -> Goa",
                "source": "Hyderabad",
                "days": 4,
                "is_multi_destination": True,
                "travel_mode": "car",
                "travelers": [{"name": "Bob", "interests": ["Beaches", "Parks"], "budget": "Medium", "pace": "Balanced"}],
                "destinations": [
                    {
                        "name": "Bengaluru",
                        "days": 2,
                        "start_day": 1,
                        "end_day": 2,
                        "location": {"lat": 12.9716, "lon": 77.5946},
                    },
                    {
                        "name": "Goa",
                        "days": 2,
                        "start_day": 3,
                        "end_day": 4,
                        "location": {"lat": 15.2993, "lon": 74.1240},
                    },
                ],
                "places": [
                    {"name": "Lalbagh Botanical Garden", "category": "Garden", "lat": 12.9507, "lon": 77.5848, "score": 4.6},
                    {"name": "Cubbon Park", "category": "Park", "lat": 12.9763, "lon": 77.5929, "score": 4.5, "description": "Lush green city park"},
                    {"name": "Baga Beach", "category": "Beach", "lat": 15.5553, "lon": 73.7517, "score": 4.7},
                    {"name": "Anjuna Beach", "category": "Beach", "lat": 15.5833, "lon": 73.7410, "score": 4.4, "description": "Iconic beach destination"},
                ],
                "day_schedule": {
                    "1": [
                        {"name": "Lalbagh Botanical Garden", "category": "Garden", "lat": 12.9507, "lon": 77.5848, "score": 4.6},
                    ],
                    "2": [],
                    "3": [
                        {"name": "Baga Beach", "category": "Beach", "lat": 15.5553, "lon": 73.7517, "score": 4.7},
                    ],
                    "4": [],
                },
                "budget": {"total_budget": 30000, "estimated_cost": 22000, "remaining": 8000},
                "excluded_places": [],
            }
        }
    return trip_data


def test_remove_attraction_and_keep_slot_empty():
    raw_trip = _build_test_trip()
    trip_id = save_trip(raw_trip)

    # Remove "Golconda Fort" from Day 1 and keep empty
    req_body = {
        "day": "1",
        "attraction_name": "Golconda Fort",
        "action": "remove",
    }
    res = client.post(f"/trip/{trip_id}/attraction-action", json=req_body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert "successfully removed" in data["message"]

    day1_places = data["trip"]["day_schedule"]["1"]
    assert len(day1_places) == 2
    place_names = [p["name"] for p in day1_places]
    assert "Golconda Fort" not in place_names
    # Preserves ordering of remaining activities
    assert place_names == ["Charminar", "Chowmahalla Palace"]

    # Day 2 is completely preserved
    day2_places = data["trip"]["day_schedule"]["2"]
    assert len(day2_places) == 2
    assert [p["name"] for p in day2_places] == ["Birla Mandir", "Salar Jung Museum"]

    # Excluded places recorded
    assert "Golconda Fort" in data["trip"]["excluded_places"]

    # Verify transit times recalculation
    assert day1_places[0]["travel_from_previous_km"] is None
    assert day1_places[1]["travel_from_previous_km"] is not None

    # Verify persistence after reload
    reloaded = load_trip(trip_id)
    assert reloaded is not None
    inner = reloaded.get("trip", reloaded)
    assert len(inner["day_schedule"]["1"]) == 2
    assert [p["name"] for p in inner["day_schedule"]["1"]] == ["Charminar", "Chowmahalla Palace"]


def test_replace_attraction_with_valid_alternative():
    raw_trip = _build_test_trip()
    trip_id = save_trip(raw_trip)

    replacement = {
        "name": "Qutb Shahi Tombs",
        "category": "Heritage Monument",
        "lat": 17.3920,
        "lon": 78.4010,
        "score": 4.4,
        "description": "Historic royal necropolis",
    }

    req_body = {
        "day": "1",
        "attraction_name": "Golconda Fort",
        "action": "replace",
        "replacement_place": replacement,
    }
    res = client.post(f"/trip/{trip_id}/attraction-action", json=req_body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True

    day1_places = data["trip"]["day_schedule"]["1"]
    assert len(day1_places) == 3
    # In-place slot replacement preserves position
    assert [p["name"] for p in day1_places] == ["Charminar", "Qutb Shahi Tombs", "Chowmahalla Palace"]

    # Day 2 completely preserved
    assert len(data["trip"]["day_schedule"]["2"]) == 2

    # Old attraction added to excluded places
    assert "Golconda Fort" in data["trip"]["excluded_places"]

    # Persistence verification
    reloaded = load_trip(trip_id)
    inner = reloaded.get("trip", reloaded)
    assert inner["day_schedule"]["1"][1]["name"] == "Qutb Shahi Tombs"


def test_alternatives_endpoint_excludes_removed_and_scheduled_places():
    raw_trip = _build_test_trip()
    trip_id = save_trip(raw_trip)

    # Day 1 has Charminar, Golconda Fort, Chowmahalla Palace
    # Day 2 has Birla Mandir, Salar Jung Museum
    # Candidate pool in trip places also includes: Qutb Shahi Tombs, Nehru Zoological Park
    res = client.get(f"/trip/{trip_id}/attraction-alternatives?day=1&attraction_name=Golconda%20Fort")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True

    alt_names = [a["name"] for a in data["alternatives"]]
    # Should include available candidates
    assert "Qutb Shahi Tombs" in alt_names
    assert "Nehru Zoological Park" in alt_names

    # MUST NOT include the removed attraction
    assert "Golconda Fort" not in alt_names

    # MUST NOT include attractions already scheduled in Day 1 or Day 2
    assert "Charminar" not in alt_names
    assert "Chowmahalla Palace" not in alt_names
    assert "Birla Mandir" not in alt_names
    assert "Salar Jung Museum" not in alt_names

    # Alternatives must provide necessary information (name, category, description)
    for alt in data["alternatives"]:
        assert alt.get("name")
        assert alt.get("category")
        assert alt.get("description")


def test_no_alternatives_available_handled_gracefully():
    raw_trip = _build_test_trip()
    # Filter trip places so ONLY currently scheduled places exist
    scheduled_names = {"Charminar", "Golconda Fort", "Chowmahalla Palace", "Birla Mandir", "Salar Jung Museum"}
    raw_trip["trip"]["places"] = [p for p in raw_trip["trip"]["places"] if p["name"] in scheduled_names]
    trip_id = save_trip(raw_trip)

    # Patch external get_places to return empty to simulate no external API results
    with patch("backend.services.external.place_service.get_places", return_value=[]):
        res = client.get(f"/trip/{trip_id}/attraction-alternatives?day=1&attraction_name=Golconda%20Fort")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["alternatives"]) == 0

    # User can still remove and keep slot empty
    remove_res = client.post(f"/trip/{trip_id}/attraction-action", json={
        "day": "1",
        "attraction_name": "Golconda Fort",
        "action": "remove",
    })
    assert remove_res.status_code == 200
    assert len(remove_res.json()["trip"]["day_schedule"]["1"]) == 2


def test_replace_with_duplicate_scheduled_attraction_fails():
    raw_trip = _build_test_trip()
    trip_id = save_trip(raw_trip)

    # Attempt to replace Day 1 "Golconda Fort" with "Birla Mandir" (already on Day 2)
    duplicate_replacement = {
        "name": "Birla Mandir",
        "category": "Temple",
        "lat": 17.4062,
        "lon": 78.4691,
    }
    req_body = {
        "day": "1",
        "attraction_name": "Golconda Fort",
        "action": "replace",
        "replacement_place": duplicate_replacement,
    }
    res = client.post(f"/trip/{trip_id}/attraction-action", json=req_body)
    assert res.status_code == 400
    assert "already scheduled" in res.text

    # Day 1 and 2 remain unaffected
    reloaded = load_trip(trip_id)
    inner = reloaded.get("trip", reloaded)
    assert len(inner["day_schedule"]["1"]) == 3
    assert inner["day_schedule"]["1"][1]["name"] == "Golconda Fort"


def test_persistence_failure_preserves_previous_itinerary():
    raw_trip = _build_test_trip()
    trip_id = save_trip(raw_trip)

    # Monkeypatch update_saved_trip to simulate storage failure
    with patch("backend.routes.update_trip.update_saved_trip", side_effect=IOError("Storage write failure")):
        res = client.post(f"/trip/{trip_id}/attraction-action", json={
            "day": "1",
            "attraction_name": "Golconda Fort",
            "action": "remove",
        })
        assert res.status_code == 500
        assert "Failed to persist itinerary updates" in res.text

    # Original trip data is preserved in store
    reloaded = load_trip(trip_id)
    inner = reloaded.get("trip", reloaded)
    assert len(inner["day_schedule"]["1"]) == 3
    assert inner["day_schedule"]["1"][1]["name"] == "Golconda Fort"


def test_multi_destination_itinerary_alternatives_and_replacement():
    raw_trip = _build_test_trip(is_multi=True)
    trip_id = save_trip(raw_trip)

    # Day 1 is in Bengaluru (Stop 1, Days 1-2)
    # Query alternatives for Day 1
    res = client.get(f"/trip/{trip_id}/attraction-alternatives?day=1&attraction_name=Lalbagh%20Botanical%20Garden")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["destination"] == "Bengaluru"
    alt_names = [a["name"] for a in data["alternatives"]]
    assert "Cubbon Park" in alt_names

    # Replace on Day 1
    rep_res = client.post(f"/trip/{trip_id}/attraction-action", json={
        "day": "1",
        "attraction_name": "Lalbagh Botanical Garden",
        "action": "replace",
        "replacement_place": {
            "name": "Cubbon Park",
            "category": "Park",
            "lat": 12.9763,
            "lon": 77.5929,
            "score": 4.5,
            "description": "Lush green city park",
        },
    })
    assert rep_res.status_code == 200
    updated_trip = rep_res.json()["trip"]
    assert updated_trip["day_schedule"]["1"][0]["name"] == "Cubbon Park"

    # Day 3 (Goa) remains unchanged
    assert updated_trip["day_schedule"]["3"][0]["name"] == "Baga Beach"


def test_nonexistent_day_or_attraction_errors():
    raw_trip = _build_test_trip()
    trip_id = save_trip(raw_trip)

    # Invalid day
    res_bad_day = client.post(f"/trip/{trip_id}/attraction-action", json={
        "day": "99",
        "attraction_name": "Charminar",
        "action": "remove",
    })
    assert res_bad_day.status_code == 404

    # Non-existent attraction on Day 1
    res_bad_attraction = client.post(f"/trip/{trip_id}/attraction-action", json={
        "day": "1",
        "attraction_name": "Taj Mahal",
        "action": "remove",
    })
    assert res_bad_attraction.status_code == 404
