import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.realtime_replanner import replan_active_day
from backend.services.storage.trip_store import load_trip, save_trip

client = TestClient(app)

def test_realtime_replanner_unit():
    print("Testing realtime day replanner service logic...")
    sample_trip = {
        "destination": "Goa",
        "travel_mode": "car",
        "day_schedule": {
            "1": [
                {"name": "Calangute Beach", "lat": 15.54, "lon": 73.75, "travel_from_previous_km": 0.0},
                {"name": "Baga Beach", "lat": 15.55, "lon": 73.75, "travel_from_previous_km": 1.5},
                {"name": "Anjuna Flea Market", "lat": 15.58, "lon": 73.74, "travel_from_previous_km": 4.0},
            ]
        },
        "places": [
            {"name": "Calangute Beach", "lat": 15.54, "lon": 73.75, "score": 8},
            {"name": "Baga Beach", "lat": 15.55, "lon": 73.75, "score": 8},
            {"name": "Anjuna Flea Market", "lat": 15.58, "lon": 73.74, "score": 7},
            {"name": "Chapora Fort", "lat": 15.60, "lon": 73.73, "score": 9},
            {"name": "Vagator Beach", "lat": 15.59, "lon": 73.73, "score": 8},
            {"name": "Museum of Goa", "lat": 15.51, "lon": 73.79, "score": 7},
        ]
    }

    # Traveler has already visited Calangute Beach, has 2.5 hours remaining, near Baga
    updated_trip, audit = replan_active_day(
        trip_data=sample_trip,
        day_number=1,
        completed_attraction_names=["Calangute Beach"],
        remaining_hours=2.5,
        current_location={"lat": 15.55, "lon": 73.75},
        current_location_name="Near Baga Beach",
    )

    assert audit["success"] is True
    assert audit["completed_count"] == 1
    assert audit["replanned_count"] >= 1

    day1_places = updated_trip["day_schedule"]["1"]
    # First place MUST be the completed Calangute Beach
    assert day1_places[0]["name"] == "Calangute Beach"
    assert day1_places[0]["is_completed"] is True

    # Calangute Beach must NOT appear twice in the list
    names = [p["name"] for p in day1_places]
    assert names.count("Calangute Beach") == 1

    # Any new places must have timing status indicating replanning
    for p in day1_places[1:]:
        assert p["is_completed"] is False
        assert "Replanned" in p.get("timing_status", "")
        print(f"Replanned stop: {p['name']} -> {p.get('time_window')}")

    print("Realtime day replanner unit test verified!")


def test_realtime_replanner_api():
    print("Testing /trip/{trip_id}/replan-day API endpoint...")
    # First create a mock trip in store
    mock_id = save_trip({
        "destination": "Goa",
        "travel_mode": "car",
        "day_schedule": {
            "1": [
                {"name": "Basilica of Bom Jesus", "lat": 15.50, "lon": 73.91, "travel_from_previous_km": 0.0},
                {"name": "Se Cathedral", "lat": 15.50, "lon": 73.91, "travel_from_previous_km": 0.3},
                {"name": "Reis Magos Fort", "lat": 15.49, "lon": 73.80, "travel_from_previous_km": 12.0},
            ]
        },
        "places": [
            {"name": "Basilica of Bom Jesus", "lat": 15.50, "lon": 73.91, "score": 9},
            {"name": "Se Cathedral", "lat": 15.50, "lon": 73.91, "score": 8},
            {"name": "Reis Magos Fort", "lat": 15.49, "lon": 73.80, "score": 8},
            {"name": "Aguada Fort", "lat": 15.49, "lon": 73.77, "score": 9},
            {"name": "Sinquerim Beach", "lat": 15.49, "lon": 73.76, "score": 7},
        ]
    })

    payload = {
        "day": 1,
        "completed_attractions": ["Basilica of Bom Jesus"],
        "remaining_hours": 3.0,
        "current_location_name": "Old Goa Heritage Walk",
    }

    res = client.post(f"/trip/{mock_id}/replan-day", json=payload)
    assert res.status_code == 200, f"API failed: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert "audit" in data
    assert "trip" in data

    saved = load_trip(mock_id)
    assert saved is not None
    day1_places = saved.get("day_schedule", {}).get("1", [])
    assert len(day1_places) >= 2
    assert day1_places[0]["name"] == "Basilica of Bom Jesus"
    assert day1_places[0].get("is_completed") is True

    print("API replan-day response summary:", data["audit"]["summary"])
    print("Step 54 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_realtime_replanner_unit()
    test_realtime_replanner_api()
