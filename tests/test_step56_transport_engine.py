import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.transport_recommendation_engine import (
    estimate_mode_metrics,
    generate_transport_recommendations,
    switch_trip_transport,
)
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)

def test_estimate_mode_metrics():
    print("Testing estimate_mode_metrics...")
    # Distance 400km, group of 4
    car_metrics = estimate_mode_metrics("car", distance_km=400, party_size=4)
    assert car_metrics["viable"] is True
    assert car_metrics["total_cost_inr"] > 0
    assert car_metrics["per_person_cost_inr"] == round(car_metrics["total_cost_inr"] / 4)
    assert car_metrics["duration_hours"] > 0

    # Short distance flight should not be viable
    flight_short = estimate_mode_metrics("flight", distance_km=100, party_size=1)
    assert flight_short["viable"] is False

    # Long distance flight
    flight_long = estimate_mode_metrics("flight", distance_km=800, party_size=1)
    assert flight_long["viable"] is True
    assert flight_long["duration_hours"] < 5.0
    print("estimate_mode_metrics OK!")


def test_generate_transport_recommendations():
    print("Testing generate_transport_recommendations...")
    # For a large group (4 people) traveling 350 km, car or train should score very high
    recs = generate_transport_recommendations(
        source="Bengaluru",
        destination="Chennai",
        distance_km=350,
        current_mode="car",
        party_size=4,
    )
    assert "recommended_mode" in recs
    assert recs["recommended_mode"] in ["car", "train", "flight", "bus"]
    assert "recommendation_summary" in recs
    assert "options" in recs
    assert "car" in recs["options"]
    assert "train" in recs["options"]
    assert "flight" in recs["options"]
    assert "bus" in recs["options"]

    # Verify badges assigned
    all_badges = [b for opt in recs["options"].values() for b in opt.get("badges", [])]
    assert any("Economical" in b for b in all_badges)
    assert any("Fastest" in b for b in all_badges)
    assert any("Eco Champion" in b for b in all_badges)
    print("generate_transport_recommendations OK!")


def test_switch_trip_transport():
    print("Testing switch_trip_transport...")
    sample_trip = {
        "source": "Hyderabad",
        "destination": "Bengaluru",
        "travel_mode": "car",
        "route": {"distance_km": 570.0, "duration_hours": 9.5},
        "travelers": [{"name": "User 1", "budget": 10000}],
        "budget": {"categories": {"transport": 5000, "hotel": 5000, "food": 3000, "activities": 2000}, "total_cost": 15000},
        "dashboard": {"travel_mode": "car", "duration": 9.5},
    }

    updated, audit = switch_trip_transport(sample_trip, "train")
    assert audit["success"] is True
    assert updated["travel_mode"] == "train"
    assert updated["transport"]["travel_mode"] == "train"
    assert "transport_recommendations" in updated
    assert updated["dashboard"]["travel_mode"] == "train"
    print("switch_trip_transport OK!")


def test_switch_transport_api():
    print("Testing POST /trip/{trip_id}/switch-transport API endpoint...")
    trip_data = {
        "source": "Mumbai",
        "destination": "Goa",
        "travel_mode": "car",
        "route": {"distance_km": 580.0, "duration_hours": 10.0},
        "travelers": [{"name": "Traveler A", "budget": 15000}],
        "budget": {"categories": {"transport": 5000, "hotel": 8000, "food": 4000, "activities": 3000}, "total_cost": 20000},
        "dashboard": {"travel_mode": "car", "duration": 10.0},
    }
    trip_id = save_trip({"trip": trip_data, "dashboard": trip_data["dashboard"]})

    res = client.post(
        f"/trip/{trip_id}/switch-transport",
        json={"travel_mode": "flight"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["trip"]["travel_mode"] == "flight"
    assert body["audit"]["new_mode"] == "flight"

    # Verify persisted in store
    saved = load_trip(trip_id)
    assert saved is not None
    assert saved["trip"]["travel_mode"] == "flight"
    print("Step 56 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_estimate_mode_metrics()
    test_generate_transport_recommendations()
    test_switch_trip_transport()
    test_switch_transport_api()
