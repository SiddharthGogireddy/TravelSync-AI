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


def test_all_three_modes_distinct_allocations_and_costs():
    """
    Step 57 Regression Test:
    Applies Experience Focused, Conservative & Balanced, and Cost Saver to the exact same trip.
    Verifies that:
    1. Each mode produces distinct category allocations according to strategic weights.
    2. Total estimated trip cost is distinct across all 3 modes:
       Cost Saver < Conservative < Experience.
    3. User's total budget remains constant and separate from estimated cost.
    4. Remaining balance equals total_budget - estimated_cost and matches retained reserve.
    5. Dashboard and analytics synchronize accurately with each mode's budget.
    """
    sample_trip = {
        "destination": "Goa",
        "days": 3,
        "travelers": [{"name": "Priya", "budget": 30000}],
        "budget": {
            "total_budget": 30000,
            "estimated_cost": 30000,
            "remaining": 0,
            "status": "Near Budget",
            "categories": {
                "hotel": 11400,
                "food": 7500,
                "transport": 5100,
                "activities": 3000,
                "emergency": 3000,
            },
        },
        "dashboard": {
            "total_budget": 30000,
            "estimated_cost": 30000,
        },
    }

    import copy

    # 1. Experience Focused
    trip_exp, audit_exp = apply_budget_reallocation(copy.deepcopy(sample_trip), strategy="experience")
    b_exp = trip_exp["budget"]
    d_exp = trip_exp["dashboard"]

    # 2. Conservative & Balanced
    trip_cons, audit_cons = apply_budget_reallocation(copy.deepcopy(sample_trip), strategy="conservative")
    b_cons = trip_cons["budget"]
    d_cons = trip_cons["dashboard"]

    # 3. Cost Saver / High Reserve
    trip_save, audit_save = apply_budget_reallocation(copy.deepcopy(sample_trip), strategy="cost_saver")
    b_save = trip_save["budget"]
    d_save = trip_save["dashboard"]

    # --- Total Budget Integrity ---
    assert b_exp["total_budget"] == 30000
    assert b_cons["total_budget"] == 30000
    assert b_save["total_budget"] == 30000

    # --- Distinct Estimated Cost Behavior ---
    assert b_save["estimated_cost"] == 24600   # 82% direct operational spend
    assert b_cons["estimated_cost"] == 27000   # 90% direct operational spend
    assert b_exp["estimated_cost"] == 28200    # 94% direct operational spend

    assert b_save["estimated_cost"] < b_cons["estimated_cost"] < b_exp["estimated_cost"]

    # --- Remaining Balance & Reserve Buffer ---
    assert b_save["remaining"] == 5400  # 18% reserve
    assert b_cons["remaining"] == 3000  # 10% reserve
    assert b_exp["remaining"] == 1800   # 6% reserve

    assert b_save["remaining"] > b_cons["remaining"] > b_exp["remaining"]

    # Total Budget = Estimated Cost + Remaining
    assert b_save["total_budget"] == b_save["estimated_cost"] + b_save["remaining"]
    assert b_cons["total_budget"] == b_cons["estimated_cost"] + b_cons["remaining"]
    assert b_exp["total_budget"] == b_exp["estimated_cost"] + b_exp["remaining"]

    # --- Category Allocation Distinctions ---
    # Activities: Experience invests heavily, Cost Saver / Conservative spend less
    assert b_exp["categories"]["activities"] == 6600
    assert b_cons["categories"]["activities"] == 3000
    assert b_save["categories"]["activities"] == 3600
    assert b_exp["categories"]["activities"] > b_cons["categories"]["activities"]

    # Dining: Experience invests most in culinary tours
    assert b_exp["categories"]["food"] == 8400
    assert b_cons["categories"]["food"] == 7500
    assert b_save["categories"]["food"] == 6600
    assert b_exp["categories"]["food"] > b_cons["categories"]["food"] > b_save["categories"]["food"]

    # Lodging: Conservative prioritizes hotel comfort
    assert b_cons["categories"]["hotel"] == 11400
    assert b_save["categories"]["hotel"] == 9600
    assert b_exp["categories"]["hotel"] == 9000
    assert b_cons["categories"]["hotel"] > b_exp["categories"]["hotel"]

    # --- Dashboard Synchronization ---
    assert d_save["estimated_cost"] == b_save["estimated_cost"]
    assert d_cons["estimated_cost"] == b_cons["estimated_cost"]
    assert d_exp["estimated_cost"] == b_exp["estimated_cost"]

    assert d_save["total_budget"] == 30000
    assert d_cons["total_budget"] == 30000
    assert d_exp["total_budget"] == 30000

    assert d_save["remaining"] == b_save["remaining"]
    assert d_cons["remaining"] == b_cons["remaining"]
    assert d_exp["remaining"] == b_exp["remaining"]


if __name__ == "__main__":
    test_analyze_budget_reallocations()
    test_apply_budget_reallocation()
    test_reallocate_budget_api()
    test_all_three_modes_distinct_allocations_and_costs()
