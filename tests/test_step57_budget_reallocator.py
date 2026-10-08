import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.budget_reallocator import (
    analyze_budget_reallocations,
    apply_budget_reallocation,
)
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)

def test_analyze_budget_reallocations():
    print("Testing analyze_budget_reallocations...")
    mock_budget = {
        "total_budget": 30000,
        "estimated_cost": 28000,
        "remaining": 2000,
        "status": "Near Budget",
        "categories": {
            "hotel": 15000,      # Over-allocated (53%)
            "food": 5000,
            "transport": 4000,
            "activities": 2000,  # Underfunded (7%)
            "emergency": 2000,
        },
    }

    # 1. Conservative strategy
    conservative_analysis = analyze_budget_reallocations(mock_budget, strategy="conservative")
    assert conservative_analysis["active_strategy"] == "conservative"
    assert "categories" in conservative_analysis
    assert conservative_analysis["categories"]["hotel"]["target_percentage"] == 38
    # Hotel was 15000, proposed is ~11400 -> negative delta (surplus to shift)
    assert conservative_analysis["categories"]["hotel"]["delta_amount"] < 0
    assert len(conservative_analysis["trade_off_suggestions"]) > 0

    # 2. Experience Maximizer strategy
    experience_analysis = analyze_budget_reallocations(mock_budget, strategy="experience")
    assert experience_analysis["active_strategy"] == "experience"
    # Activities target should be 22%
    assert experience_analysis["categories"]["activities"]["target_percentage"] == 22
    assert experience_analysis["categories"]["activities"]["proposed_amount"] > mock_budget["categories"]["activities"]
    print("analyze_budget_reallocations OK!")


def test_apply_budget_reallocation():
    print("Testing apply_budget_reallocation...")
    sample_trip = {
        "budget": {
            "total_budget": 35000,
            "estimated_cost": 32000,
            "remaining": 3000,
            "status": "Near Budget",
            "categories": {
                "hotel": 16000,
                "food": 7000,
                "transport": 5000,
                "activities": 2000,
                "emergency": 2000,
            },
        }
    }

    updated_trip, audit = apply_budget_reallocation(sample_trip, strategy="experience")
    assert audit["success"] is True
    assert "budget_reallocation" in updated_trip
    # Activities should have received more funds in experience mode
    new_categories = updated_trip["budget"]["categories"]
    assert new_categories["activities"] > 2000
    assert updated_trip["budget"]["category_percentage"]["activities"] >= 20
    print("apply_budget_reallocation OK!")


def test_reallocate_budget_api():
    print("Testing POST /trip/{trip_id}/reallocate-budget API endpoint...")
    trip_data = {
        "destination": "Jaipur",
        "budget": {
            "total_budget": 40000,
            "estimated_cost": 36000,
            "remaining": 4000,
            "status": "Near Budget",
            "categories": {
                "hotel": 20000,
                "food": 8000,
                "transport": 4000,
                "activities": 2000,
                "emergency": 2000,
            },
        }
    }
    trip_id = save_trip({"trip": trip_data})

    res = client.post(
        f"/trip/{trip_id}/reallocate-budget",
        json={"strategy": "cost_saver"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["trip"]["budget"]["categories"]["emergency"] > 2000

    saved = load_trip(trip_id)
    assert saved is not None
    assert saved["trip"]["budget"]["categories"]["emergency"] > 2000
    print("Step 57 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_analyze_budget_reallocations()
    test_apply_budget_reallocation()
    test_reallocate_budget_api()
