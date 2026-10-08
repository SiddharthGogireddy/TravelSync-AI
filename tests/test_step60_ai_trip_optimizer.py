import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.ai_trip_optimizer import (
    calculate_trip_optimization_score,
    optimize_trip_itinerary,
)
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)


def build_sample_trip():
    return {
        "source": "Bengaluru",
        "destination": "Mysuru",
        "duration": 2,
        "travel_mode": "car",
        "travelers": [
            {"name": "Alice", "budget": 10000, "interests": ["nature", "culture"]},
            {"name": "Bob", "budget": 12000, "interests": ["food", "history"]},
        ],
        "budget": {
            "total_budget": 22000,
            "status": "Near Budget",
            "remaining": 1500,
            "categories": {"stay": 10000, "food": 5000, "activities": 4000, "buffer": 1500},
        },
        "day_schedule": {
            "Day 1": [
                {
                    "name": "Mysore Palace",
                    "lat": 12.3052,
                    "lon": 76.6552,
                    "category": "Historic Site",
                    "travel_from_previous_km": 0.0,
                    "travel_time_minutes": 0,
                    "time_window": "09:00 AM",
                },
                {
                    "name": "Brindavan Gardens",
                    "lat": 12.4244,
                    "lon": 76.5728,
                    "category": "Garden",
                    "travel_from_previous_km": 20.0,
                    "travel_time_minutes": 40,
                    "time_window": "11:30 AM",
                },
                {
                    "name": "St Philomena Church",
                    "lat": 12.3214,
                    "lon": 76.6586,
                    "category": "Architecture",
                    "travel_from_previous_km": 19.5,
                    "travel_time_minutes": 38,
                    "time_window": "02:00 PM",
                },
                {
                    "name": "Chamundi Hills",
                    "lat": 12.2748,
                    "lon": 76.6706,
                    "category": "Nature",
                    "travel_from_previous_km": 8.0,
                    "travel_time_minutes": 20,
                    "time_window": "04:30 PM",
                },
            ],
            "Day 2": [
                {
                    "name": "KRS Dam",
                    "lat": 12.4262,
                    "lon": 76.5745,
                    "category": "Dam",
                    "travel_from_previous_km": 0.0,
                    "travel_time_minutes": 0,
                    "time_window": "09:00 AM",
                },
                {
                    "name": "Railway Museum",
                    "lat": 12.3165,
                    "lon": 76.6450,
                    "category": "Museum",
                    "travel_from_previous_km": 18.0,
                    "travel_time_minutes": 35,
                    "time_window": "11:30 AM",
                },
            ],
        },
    }


def test_calculate_trip_optimization_score():
    sample_trip = build_sample_trip()
    score_data = calculate_trip_optimization_score(sample_trip)

    assert "overall_score" in score_data
    assert 0 <= score_data["overall_score"] <= 100
    assert "quality_tier" in score_data
    assert "tier_badge" in score_data
    assert "metrics" in score_data

    metrics = score_data["metrics"]
    assert "route_efficiency" in metrics
    assert "pacing_score" in metrics
    assert "budget_adherence" in metrics
    assert "traveler_happiness" in metrics

    assert 0 <= metrics["route_efficiency"] <= 100
    assert 0 <= metrics["pacing_score"] <= 100
    assert 0 <= metrics["budget_adherence"] <= 100
    assert 0 <= metrics["traveler_happiness"] <= 100

    stats = score_data["stats"]
    assert stats["total_days"] == 2
    assert stats["total_places"] == 6
    assert stats["total_transit_km"] > 0

    assert len(score_data["recommendations"]) > 0
    print("[PASS] test_calculate_trip_optimization_score passed")


def test_optimize_trip_itinerary_tsp():
    sample_trip = build_sample_trip()
    initial_score = calculate_trip_optimization_score(sample_trip)

    # In Day 1, Church is 2 km from Palace, but Gardens was inserted in between (20 km zig-zag)
    optimized_trip, audit = optimize_trip_itinerary(sample_trip)

    assert audit["success"] is True
    assert "saved_distance_km" in audit
    assert "saved_transit_minutes" in audit
    assert audit["days_optimized"] >= 1
    assert "summary" in audit

    day1 = optimized_trip["day_schedule"]["Day 1"]
    assert any(p.get("is_ai_optimized") for p in day1)

    # Reordered places should follow nearest neighbor
    assert day1[0]["name"] == "Mysore Palace"
    assert day1[1]["name"] == "St Philomena Church"
    assert day1[1]["travel_from_previous_km"] < 5.0

    assert "optimization_score" in optimized_trip
    assert optimized_trip["optimization_score"]["overall_score"] >= initial_score["overall_score"]
    print("[PASS] test_optimize_trip_itinerary_tsp passed")


def test_get_optimization_score_endpoint():
    sample_trip = build_sample_trip()
    trip_id = save_trip({"trip": sample_trip})

    response = client.get(f"/trip/{trip_id}/optimization-score")
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["success"] is True
    assert "optimization_score" in data
    assert data["optimization_score"]["overall_score"] > 0
    print("[PASS] test_get_optimization_score_endpoint passed")


def test_optimize_trip_endpoint():
    sample_trip = build_sample_trip()
    trip_id = save_trip({"trip": sample_trip})

    response = client.post(f"/trip/{trip_id}/optimize-trip")
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["success"] is True
    assert "trip" in data
    assert "audit" in data
    assert data["audit"]["success"] is True
    assert "saved_distance_km" in data["audit"]

    # Verify persistence in store
    loaded = load_trip(trip_id)
    inner = loaded.get("trip", loaded)
    assert "optimization_score" in inner
    assert inner["optimization_score"]["overall_score"] > 0
    print("[PASS] test_optimize_trip_endpoint passed")


def test_optimize_trip_not_found():
    response = client.post("/trip/nonexistent-trip-id-9999/optimize-trip")
    assert response.status_code == 404
    print("[PASS] test_optimize_trip_not_found passed")


if __name__ == "__main__":
    test_calculate_trip_optimization_score()
    test_optimize_trip_itinerary_tsp()
    test_get_optimization_score_endpoint()
    test_optimize_trip_endpoint()
    test_optimize_trip_not_found()
    print("Step 60 tests ALL PASSED SUCCESSFULLY!")
