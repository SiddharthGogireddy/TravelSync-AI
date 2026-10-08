import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.models.trip import PlanningConstraints
from backend.services.planner.constraint_engine import validate_constraints, evaluate_constraints
from backend.services.storage.trip_store import load_trip

client = TestClient(app)

def test_constraint_validation():
    print("Testing constraint validation rules...")
    # 1. Location in both must_visit and avoided_locations
    c_conflict = PlanningConstraints(
        must_visit=["Charminar", "Golconda"],
        avoided_locations=["Charminar"],
        max_budget=1000.0
    )
    res_conflict = validate_constraints(c_conflict)
    assert not res_conflict["valid"]
    assert any("both must-visit and avoided" in e for e in res_conflict["errors"])
    print("Conflict test passed!")

    # 2. Negative budget or negative distance
    c_neg = PlanningConstraints(max_budget=-100.0, max_daily_distance_km=-5.0)
    res_neg = validate_constraints(c_neg)
    assert not res_neg["valid"]
    assert len(res_neg["errors"]) >= 2
    print("Negative value validation test passed!")

    # 3. Valid constraints
    c_valid = PlanningConstraints(
        must_visit=["Eiffel Tower"],
        avoided_locations=["Louvre Museum"],
        max_daily_distance_km=25.0,
        max_budget=2000.0,
        preferred_pace="relaxed"
    )
    res_valid = validate_constraints(c_valid)
    assert res_valid["valid"]
    assert len(res_valid["errors"]) == 0
    print("Valid constraint validation passed!")

def test_planner_with_constraints():
    print("Testing /planner/ endpoint with planning constraints...")
    payload = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Goa, India",
        "days": 2,
        "travelers": [
            {
                "name": "Sarah",
                "interests": ["Beaches", "Food"],
                "budget": "Medium",
                "pace": "Relaxed"
            }
        ],
        "mandatory_visits": [],
        "travel_mode": "car",
        "constraints": {
            "must_visit": ["Baga Beach"],
            "avoided_locations": ["Calangute Beach"],
            "max_daily_distance_km": 50.0,
            "max_budget": 5000.0,
            "preferred_pace": "relaxed"
        }
    }

    res = client.post("/planner/", json=payload)
    assert res.status_code == 200, f"Planner request failed: {res.text}"
    data = res.json()
    assert "trip_id" in data
    trip_id = data["trip_id"]

    saved_trip = load_trip(trip_id)
    assert saved_trip is not None
    trip_data = saved_trip.get("trip", {})

    assert "constraint_analysis" in trip_data
    ca = trip_data["constraint_analysis"]
    print("FULL CONSTRAINT ANALYSIS RESULT:", ca)
    assert ca["satisfied"]["must_visit"] is True
    assert ca["satisfied"]["avoided_locations"] is True


    # Ensure avoided location Calangute Beach is NOT in scheduled attractions
    scheduled_places = []
    for day_places in trip_data.get("day_schedule", {}).values():
        for p in day_places:
            scheduled_places.append(p.get("name", "").lower())
    for day in trip_data.get("itinerary", []):
        for p in day.get("places", []):
            scheduled_places.append(p.get("name", "").lower())

    for place_name in scheduled_places:
        assert "calangute" not in place_name, f"Avoided place {place_name} was found in itinerary!"

    
    print("Avoided location exclusion verified successfully!")
    print("Step 50 test complete and ALL PASSED!")

if __name__ == "__main__":
    test_constraint_validation()
    test_planner_with_constraints()
