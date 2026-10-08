import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.storage.trip_store import load_trip

client = TestClient(app)

def test_single_and_multi_destination():
    # 1. Test single-destination trip (backward compatibility test)
    single_req = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Goa, India",
        "days": 3,
        "travelers": [
            {
                "name": "Alex",
                "interests": ["Beaches", "Food"],
                "budget": "Medium",
                "pace": "Balanced"
            }
        ],
        "mandatory_visits": [],
        "travel_mode": "car"
    }
    single_res = client.post("/planner/", json=single_req)
    assert single_res.status_code == 200, f"Single destination failed: {single_res.text}"
    single_data = single_res.json()
    assert "trip_id" in single_data
    single_trip_id = single_data["trip_id"]
    single_trip = load_trip(single_trip_id)
    assert single_trip is not None
    assert single_trip["trip"]["is_multi_destination"] is False
    assert single_trip["trip"]["days"] == 3
    print("Single destination test PASSED! Trip ID:", single_trip_id)

    # 2. Test multi-destination trip: Hyderabad -> Bengaluru (2 days) -> Mysuru (1 day) -> Goa (2 days)
    multi_req = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Bengaluru, Karnataka, India", # Fallback destination
        "days": 5,
        "destinations": [
            {"name": "Bengaluru, Karnataka, India", "days": 2},
            {"name": "Mysuru, Karnataka, India", "days": 1},
            {"name": "Goa, India", "days": 2}
        ],
        "travelers": [
            {
                "name": "Sarah",
                "interests": ["Nature", "History"],
                "budget": "Medium",
                "pace": "Balanced"
            },
            {
                "name": "David",
                "interests": ["Food", "Culture"],
                "budget": "Medium",
                "pace": "Relaxed"
            }
        ],
        "mandatory_visits": [],
        "travel_mode": "car"
    }
    multi_res = client.post("/planner/", json=multi_req)
    assert multi_res.status_code == 200, f"Multi destination failed: {multi_res.text}"
    multi_data = multi_res.json()
    assert "trip_id" in multi_data
    multi_trip_id = multi_data["trip_id"]

    # 3. Verify stored multi-destination trip properties
    stored_multi = load_trip(multi_trip_id)
    assert stored_multi is not None
    trip_obj = stored_multi["trip"]

    # Verify multi-destination flags and stops
    assert trip_obj.get("is_multi_destination") is True
    assert "destinations" in trip_obj
    assert len(trip_obj["destinations"]) == 3

    # Verify days calculation
    assert trip_obj["days"] == 5

    # Verify inter-destination travel legs
    assert "inter_destination_travel" in trip_obj
    travel_legs = trip_obj["inter_destination_travel"]
    assert len(travel_legs) == 3 # Leg 1: Hyd->Blr, Leg 2: Blr->Mys, Leg 3: Mys->Goa
    for leg in travel_legs:
        assert leg["distance_km"] > 0
        assert leg["duration_hours"] > 0
        assert "from_location" in leg
        assert "to_location" in leg
        assert leg["travel_mode"] == "car"
        print(f"Verified travel leg: {leg['from_location']} -> {leg['to_location']} ({leg['distance_km']} km, {leg['duration_hours']} hrs)")

    # Verify day schedule covers all 5 days
    day_schedule = trip_obj["day_schedule"]
    for day in range(1, 6):
        assert str(day) in day_schedule, f"Day {day} missing from multi-destination schedule"

    # Verify route totals
    assert trip_obj["route"]["distance_km"] > 0
    assert trip_obj["route"]["duration_hours"] > 0

    # 4. Verify API retrieval endpoint /trip/{trip_id}
    api_get_res = client.get(f"/trip/{multi_trip_id}")
    assert api_get_res.status_code == 200
    get_json = api_get_res.json()
    assert get_json["trip"]["is_multi_destination"] is True

    print("Step 48 Multi-Destination Trip Planning all backend tests PASSED successfully!")

if __name__ == "__main__":
    test_single_and_multi_destination()
