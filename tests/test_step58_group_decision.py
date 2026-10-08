import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.group_decision_engine import (
    calculate_group_alignment,
    compute_traveler_satisfaction,
    calculate_consensus_scores,
    cast_group_vote,
    resolve_group_conflicts,
    evaluate_group_decisions,
)
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)

def test_calculate_group_alignment():
    print("Testing calculate_group_alignment...")
    travelers = [
        {"name": "Alice", "interests": ["nature", "hiking"], "pace": "fast", "budget": "moderate"},
        {"name": "Bob", "interests": ["history", "museums"], "pace": "relaxed", "budget": "luxury"},
    ]
    alignment = calculate_group_alignment(travelers)
    assert alignment["harmony_score"] < 100
    assert len(alignment["divergence_zones"]) >= 2
    # Verify pace and budget conflicts are detected
    categories = [z["category"] for z in alignment["divergence_zones"]]
    assert "Pace Conflict" in categories
    assert "Budget Disparity" in categories
    print("calculate_group_alignment OK!")


def test_compute_traveler_satisfaction():
    print("Testing compute_traveler_satisfaction...")
    travelers = [
        {"name": "Alice", "interests": ["park"]},
        {"name": "Bob", "interests": ["historic"]},
    ]
    scheduled_places = [
        {"name": "Lalbagh Botanical Garden", "category": "Park"},
        {"name": "Cubbon Park", "category": "Park"},
    ]
    satisfaction = compute_traveler_satisfaction(travelers, scheduled_places)
    assert len(satisfaction) == 2
    alice = next(s for s in satisfaction if s["traveler"] == "Alice")
    bob = next(s for s in satisfaction if s["traveler"] == "Bob")
    assert alice["score"] == 100
    assert "Park" in alice["represented_interests"]
    assert "Historic" in bob["missing_interests"]
    print("compute_traveler_satisfaction OK!")


def test_cast_vote_and_resolve_conflicts():
    print("Testing cast_group_vote and resolve_group_conflicts...")
    sample_trip = {
        "travelers": [
            {"name": "Alice", "interests": ["nature"]},
            {"name": "Bob", "interests": ["history"]},
        ],
        "places": [
            {"name": "City Mall", "category": "Shopping"},
            {"name": "Ancient Fort", "category": "History"},
            {"name": "Nature Lake", "category": "Nature"},
        ],
        "day_schedule": {
            "1": [
                {"name": "City Mall", "category": "Shopping", "travel_time_minutes": 15},
            ]
        },
        "group_votes": {},
    }

    # Bob downvotes City Mall
    updated, audit = cast_group_vote(sample_trip, "Bob", "City Mall", "down")
    assert audit["success"] is True
    assert updated["group_votes"]["City Mall"]["Bob"] == "down"

    # Auto-resolve conflicts
    resolved_trip, res_audit = resolve_group_conflicts(updated)
    assert res_audit["success"] is True
    assert res_audit["swapped_count"] >= 1
    # City Mall should be replaced by a place matching Bob or Alice's interest
    day1_names = [p["name"] for p in resolved_trip["day_schedule"]["1"]]
    assert "City Mall" not in day1_names
    assert "Ancient Fort" in day1_names or "Nature Lake" in day1_names
    print("cast_group_vote and resolve_group_conflicts OK!")


def test_group_decision_api_endpoints():
    print("Testing group decision API endpoints...")
    test_trip = {
        "travelers": [
            {"name": "Rohan", "interests": ["adventure"]},
            {"name": "Priya", "interests": ["temples"]},
        ],
        "places": [
            {"name": "Crowded Bazaar", "category": "Shopping"},
            {"name": "Sun Temple", "category": "Temples"},
        ],
        "day_schedule": {
            "1": [
                {"name": "Crowded Bazaar", "category": "Shopping", "travel_time_minutes": 20},
            ]
        },
        "group_votes": {},
    }
    trip_id = save_trip({"trip": test_trip})

    # Vote API
    res_vote = client.post(
        f"/trip/{trip_id}/group-vote",
        json={"traveler_name": "Rohan", "attraction_name": "Crowded Bazaar", "vote": "down"},
    )
    assert res_vote.status_code == 200, res_vote.text
    assert res_vote.json()["success"] is True

    # Resolve API
    res_resolve = client.post(f"/trip/{trip_id}/resolve-group-conflicts")
    assert res_resolve.status_code == 200, res_resolve.text
    resolve_body = res_resolve.json()
    assert resolve_body["success"] is True
    assert resolve_body["audit"]["swapped_count"] >= 1

    saved = load_trip(trip_id)
    assert saved is not None
    day1_places = saved["trip"]["day_schedule"]["1"]
    assert any(p["name"] == "Sun Temple" for p in day1_places)
    print("Step 58 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_calculate_group_alignment()
    test_compute_traveler_satisfaction()
    test_cast_vote_and_resolve_conflicts()
    test_group_decision_api_endpoints()
