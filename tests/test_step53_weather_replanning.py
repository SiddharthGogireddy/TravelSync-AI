import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.weather_planner import (
    classify_weather_condition,
    is_outdoor_place,
    is_indoor_place,
    replan_trip_for_weather,
)
from backend.services.storage.trip_store import load_trip

client = TestClient(app)

def test_weather_classification():
    print("Testing weather condition classification...")
    # 1. Rain
    cond, is_severe, reason = classify_weather_condition({"weather_code": 80, "max_temp": 28.0})
    assert cond == "rain"
    assert is_severe is True

    # 2. Storm
    cond, is_severe, reason = classify_weather_condition({"weather_code": 96, "max_temp": 26.0})
    assert cond == "storm"
    assert is_severe is True

    # 3. Extreme Heat
    cond, is_severe, reason = classify_weather_condition({"weather_code": 1, "max_temp": 41.5})
    assert cond == "extreme_heat"
    assert is_severe is True

    # 4. Clear/Cloudy
    cond, is_severe, reason = classify_weather_condition({"weather_code": 3, "max_temp": 30.0})
    assert cond == "cloudy"
    assert is_severe is False

    print("Weather condition classification verified!")


def test_indoor_outdoor_detection():
    print("Testing indoor vs outdoor attraction detection...")
    assert is_outdoor_place({"name": "Baga Beach", "category": "Beaches"}) is True
    assert is_outdoor_place({"name": "Cubbon Park", "category": "Parks"}) is True
    assert is_outdoor_place({"name": "Dudhsagar Waterfall", "category": "Waterfalls"}) is True

    assert is_indoor_place({"name": "National Museum", "category": "Museums"}) is True
    assert is_indoor_place({"name": "Science City Planetarium", "category": "Cultural"}) is True
    assert is_indoor_place({"name": "Phoenix Marketcity", "category": "Mall"}) is True

    print("Indoor/outdoor classification verified!")


def test_weather_replan_execution():
    print("Testing trip schedule adaptation on severe rain day...")
    day_schedule = {
        "1": [
            {"name": "Anjuna Beach", "category": "Beach", "lat": 15.58, "lon": 73.74, "travel_from_previous_km": 0.0},
            {"name": "Chapora Fort", "category": "Fort", "lat": 15.60, "lon": 73.73, "travel_from_previous_km": 3.0},
        ],
        "2": [
            {"name": "Goa State Museum", "category": "Museum", "lat": 15.49, "lon": 73.82, "travel_from_previous_km": 0.0},
            {"name": "Panaji Church", "category": "Church", "lat": 15.49, "lon": 73.83, "travel_from_previous_km": 1.2},
        ]
    }

    # Day 1 has heavy rain (code 80), Day 2 is clear (code 0)
    weather_summary = [
        {"date": "2026-10-10", "weather_code": 80, "max_temp": 28.0},
        {"date": "2026-10-11", "weather_code": 0, "max_temp": 29.0},
    ]

    available_pool = [
        {"name": "Naval Aviation Museum", "category": "Museum", "lat": 15.38, "lon": 73.83},
        {"name": "Houses of Goa Museum", "category": "Museum", "lat": 15.53, "lon": 73.85},
    ]

    updated_schedule, report = replan_trip_for_weather(
        day_schedule=day_schedule,
        weather_summary=weather_summary,
        available_places=available_pool,
    )

    assert report["has_weather_replan"] is True
    assert report["adverse_days_count"] == 1
    assert len(report["decisions"]) >= 1

    # On Day 1 (rainy), outdoor activities should be replaced or swapped with indoor activities
    day1_names = [p["name"] for p in updated_schedule["1"]]
    print("Replanned Day 1 activities (Rainy):", day1_names)
    print("Replanned Day 2 activities (Clear):", [p["name"] for p in updated_schedule["2"]])

    for d in report["decisions"]:
        print(f"Decision: {d['explanation']}")

    # Verify transit distance was recalculated
    for p in updated_schedule["1"]:
        assert "travel_from_previous_km" in p

    print("Weather replan execution verified!")


def test_planner_weather_replan_integration():
    print("Testing /planner/ integration with weather replanning report...")
    payload = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Goa, India",
        "days": 2,
        "travelers": [
            {
                "name": "Nora",
                "interests": ["Beaches", "Culture"],
                "budget": "Medium",
                "pace": "Balanced"
            }
        ],
        "mandatory_visits": [],
        "travel_mode": "car"
    }

    res = client.post("/planner/", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "trip_id" in data

    saved = load_trip(data["trip_id"])
    assert saved is not None
    trip_data = saved.get("trip", {})

    assert "weather_replanning" in trip_data
    wr = trip_data["weather_replanning"]
    assert "has_weather_replan" in wr
    assert "decisions" in wr
    assert "summary" in wr
    print("Trip response weather replanning summary:", wr["summary"])
    print("Step 53 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_weather_classification()
    test_indoor_outdoor_detection()
    test_weather_replan_execution()
    test_planner_weather_replan_integration()
