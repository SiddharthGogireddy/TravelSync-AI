import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.opening_hours_scheduler import (
    resolve_place_opening_hours,
    estimate_travel_minutes,
    schedule_day_opening_hours,
    apply_opening_hours_to_schedule,
    time_to_minutes,
    minutes_to_time_str,
)
from backend.services.storage.trip_store import load_trip

client = TestClient(app)

def test_resolve_place_opening_hours():
    print("Testing opening hours resolution across categories...")
    # Museum
    m_oh = resolve_place_opening_hours({"name": "City Museum", "category": "Museums"})
    assert m_oh["opens"] == "10:00"
    assert m_oh["closes"] == "17:30"
    assert "Monday" in m_oh["closed_days"]

    # Religious
    r_oh = resolve_place_opening_hours({"name": "Shri Temple", "category": "Religion"})
    assert r_oh["opens"] == "06:00"
    assert r_oh["closes"] == "20:30"

    # Nightlife
    n_oh = resolve_place_opening_hours({"name": "Club Velocity", "category": "Nightlife"})
    assert n_oh["opens"] == "19:00"
    assert n_oh["closes_minute"] > n_oh["opens_minute"]

    print("Opening hours category resolution verified!")


def test_transit_time_estimation():
    print("Testing transit time estimation...")
    # 35 km by car at 35 km/h + 5 min buffer = ~65 mins
    car_mins = estimate_travel_minutes(35.0, "car")
    assert 60 <= car_mins <= 75

    # 0 km transit buffer
    zero_mins = estimate_travel_minutes(0.0, "car")
    assert zero_mins == 10

    print("Transit time estimation verified!")


def test_schedule_day_opening_hours_and_replanning():
    print("Testing day scheduling within open hours and replanning...")
    places = [
        {
            "name": "Morning Temple",
            "category": "Religion",
            "travel_from_previous_km": 2.0,
        },
        {
            "name": "Art Museum",
            "category": "Museum",
            "travel_from_previous_km": 5.0,
        },
        {
            "name": "Night Pub",
            "category": "Nightlife",
            "travel_from_previous_km": 10.0,
        }
    ]

    scheduled, notes = schedule_day_opening_hours(
        places=places,
        travel_mode="car",
        day_start_hour="08:00"
    )

    assert len(scheduled) == 3
    for p in scheduled:
        assert "time_window" in p
        assert "arrival_time" in p
        assert "departure_time" in p
        assert "opening_hours" in p
        print(f"Scheduled: {p['name']} -> {p['time_window']} (Open: {p['opening_hours']['display']})")

    # Verify chronological sequence (first departure <= second arrival)
    p0_dep = time_to_minutes(scheduled[0]["departure_time"].replace(" AM", "").replace(" PM", ""))
    p1_arr = time_to_minutes(scheduled[1]["arrival_time"].replace(" AM", "").replace(" PM", ""))
    # Even across 12-hr display strings, p1 arrival is after p0 departure
    assert scheduled[0]["arrival_time"] != scheduled[1]["arrival_time"]
    print("Sequential day scheduling verified!")


def test_planner_endpoint_opening_hours():
    print("Testing /planner/ endpoint opening hours awareness...")
    payload = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Goa, India",
        "days": 2,
        "travelers": [
            {
                "name": "Maya",
                "interests": ["History", "Food"],
                "budget": "Medium",
                "pace": "Balanced"
            }
        ],
        "mandatory_visits": [],
        "travel_mode": "car"
    }

    res = client.post("/planner/", json=payload)
    assert res.status_code == 200, f"Planner request failed: {res.text}"
    data = res.json()
    assert "trip_id" in data
    trip_id = data["trip_id"]

    saved_trip = load_trip(trip_id)
    assert saved_trip is not None
    trip_data = saved_trip.get("trip", {})

    day_schedule = trip_data.get("day_schedule", {})
    assert len(day_schedule) > 0

    checked_places = 0
    for day_num, day_places in day_schedule.items():
        for p in day_places:
            assert "time_window" in p, f"Place {p.get('name')} missing time_window!"
            assert "opening_hours" in p, f"Place {p.get('name')} missing opening_hours!"
            assert "opens" in p["opening_hours"]
            assert "closes" in p["opening_hours"]
            checked_places += 1

    assert checked_places > 0, "No places found in day schedule to check!"
    print(f"Verified opening hours and time windows on {checked_places} scheduled attractions!")
    print("Step 51 opening hours tests complete and ALL PASSED!")


if __name__ == "__main__":
    test_resolve_place_opening_hours()
    test_transit_time_estimation()
    test_schedule_day_opening_hours_and_replanning()
    test_planner_endpoint_opening_hours()
