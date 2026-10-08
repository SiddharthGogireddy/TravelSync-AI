import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.meal_and_break_engine import (
    plan_day_meals_and_breaks,
    attach_meals_and_breaks_to_itinerary,
    find_nearest_food_place,
)
from backend.services.storage.trip_store import load_trip

client = TestClient(app)

def test_meal_and_break_generation():
    print("Testing meal and rest break generation...")
    day_places = [
        {
            "name": "Historical Fort",
            "category": "Historic",
            "lat": 15.29,
            "lon": 74.12,
            "travel_from_previous_km": 5.0,
        },
        {
            "name": "Botanical Garden",
            "category": "Park",
            "lat": 15.31,
            "lon": 74.14,
            "travel_from_previous_km": 8.0,
        },
        {
            "name": "Sunset Beach",
            "category": "Beach",
            "lat": 15.34,
            "lon": 74.15,
            "travel_from_previous_km": 12.0,
        }
    ]

    food_places = [
        {
            "name": "Ocean View Shack",
            "category": "Foods",
            "lat": 15.34,
            "lon": 74.15,
        },
        {
            "name": "Green Veggie Cafe",
            "category": "Foods",
            "lat": 15.29,
            "lon": 74.12,
        }
    ]

    travelers = [
        {
            "name": "Liam",
            "budget": "Low",
            "interests": ["Vegetarian", "Nature"]
        }
    ]

    # Test with 25 km total travel distance
    res = plan_day_meals_and_breaks(
        day_places=day_places,
        available_places=food_places,
        day_index=1,
        travelers=travelers,
        total_day_distance_km=25.0
    )

    assert res["day"] == 1
    assert "meals" in res
    assert len(res["meals"]) == 3

    meal_types = [m["meal_type"] for m in res["meals"]]
    assert "Breakfast" in meal_types
    assert "Lunch" in meal_types
    assert "Dinner" in meal_types

    # Budget tier should be budget-friendly for "Low" budget
    assert "Budget" in res["meals"][0]["price_tier"]

    # Rest breaks should be present due to 3 attractions and 25 km distance
    assert len(res["rest_breaks"]) >= 1
    assert any("Rest Break" in rb["break_type"] for rb in res["rest_breaks"])
    print("Meal and rest break generation verified!")


def test_planner_endpoint_meals_and_breaks():
    print("Testing /planner/ endpoint meals and breaks inclusion...")
    payload = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Goa, India",
        "days": 2,
        "travelers": [
            {
                "name": "Aria",
                "interests": ["Food", "Beaches"],
                "budget": "High",
                "pace": "Relaxed"
            }
        ],
        "mandatory_visits": [],
        "travel_mode": "car"
    }

    response = client.post("/planner/", json=payload)
    assert response.status_code == 200, f"Planner request failed: {response.text}"
    data = response.json()
    assert "trip_id" in data

    saved = load_trip(data["trip_id"])
    assert saved is not None
    trip_data = saved.get("trip", {})

    assert "meals_and_breaks" in trip_data
    mb = trip_data["meals_and_breaks"]
    assert "1" in mb
    assert "2" in mb

    day1_mb = mb["1"]
    assert "meals" in day1_mb
    assert len(day1_mb["meals"]) == 3
    for meal in day1_mb["meals"]:
        assert "name" in meal
        assert "time_slot" in meal
        assert "price_tier" in meal
        assert "estimated_cost_per_person" in meal
        print(f"Day 1 {meal['meal_type']}: {meal['name']} ({meal['time_slot']}) - {meal['price_tier']}")

    assert "rest_breaks" in day1_mb
    print(f"Day 1 Rest Breaks: {len(day1_mb['rest_breaks'])}")
    print("Step 52 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_meal_and_break_generation()
    test_planner_endpoint_meals_and_breaks()
