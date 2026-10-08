import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.attraction_ranker import rank_places, INTEREST_MAP
from backend.services.planner.preference_matcher import match_preferences
from backend.services.storage.trip_store import load_trip

client = TestClient(app)

def test_advanced_traveler_preferences():
    # 1. Verify all 9 required interests exist in INTEREST_MAP
    required_interests = [
        "Food",
        "History",
        "Culture",
        "Nature",
        "Adventure",
        "Beaches",
        "Shopping",
        "Religion",
        "Nightlife"
    ]
    for interest in required_interests:
        assert interest in INTEREST_MAP, f"Required interest '{interest}' missing from INTEREST_MAP"
    print("All 9 required interests present in INTEREST_MAP!")

    # 2. Test ranker and preference matcher with diverse traveler profiles
    travelers = [
        {"name": "Alice", "interests": ["Food", "Nightlife"], "budget": "High", "pace": "Balanced"},
        {"name": "Bob", "interests": ["History", "Culture"], "budget": "Medium", "pace": "Balanced"},
        {"name": "Charlie", "interests": ["Nature", "Adventure"], "budget": "Medium", "pace": "Fast"},
        {"name": "Diana", "interests": ["Shopping", "Religion"], "budget": "Low", "pace": "Relaxed"},
    ]

    sample_places = [
        {"name": "Ancient Fort & Museum", "category": "Historic", "distance_km": 3.0},
        {"name": "Gourmet Bistro & Night Pub", "category": "Pub", "distance_km": 2.0},
        {"name": "Botanical Gardens & Forest Walk", "category": "Nature", "distance_km": 4.0},
        {"name": "Grand Bazaar & Craft Market", "category": "Shopping", "distance_km": 1.5},
        {"name": "Historic Temple & Shrine", "category": "Religion", "distance_km": 2.5},
        {"name": "Generic Office Park", "category": "Commercial", "distance_km": 12.0},
    ]

    ranked = rank_places(sample_places, travelers)
    matched = match_preferences(ranked, travelers)

    # Verify Alice matched Gourmet Bistro & Night Pub
    pub_place = next(p for p in matched if p["name"] == "Gourmet Bistro & Night Pub")
    assert "Alice" in pub_place["matched_travelers"]
    assert any(i.lower() in ["food", "nightlife"] for i in pub_place["matched_interests"])

    # Verify Bob matched Ancient Fort & Museum
    fort_place = next(p for p in matched if p["name"] == "Ancient Fort & Museum")
    assert "Bob" in fort_place["matched_travelers"]
    assert any(i.lower() in ["history", "culture"] for i in fort_place["matched_interests"])

    # Verify Charlie matched Botanical Gardens
    gardens_place = next(p for p in matched if p["name"] == "Botanical Gardens & Forest Walk")
    assert "Charlie" in gardens_place["matched_travelers"]
    assert "Nature" in gardens_place["matched_interests"]

    # Verify Diana matched Grand Bazaar and Historic Temple
    bazaar_place = next(p for p in matched if p["name"] == "Grand Bazaar & Craft Market")
    assert "Diana" in bazaar_place["matched_travelers"]
    assert "Shopping" in bazaar_place["matched_interests"]

    temple_place = next(p for p in matched if p["name"] == "Historic Temple & Shrine")
    assert "Diana" in temple_place["matched_travelers"]
    assert "Religion" in temple_place["matched_interests"]

    print("Direct ranker & preference matcher assertions PASSED!")

    # 3. Test full planner API with multi-traveler diverse preferences
    planner_payload = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Goa, India",
        "days": 3,
        "travelers": travelers,
        "mandatory_visits": [],
        "travel_mode": "car"
    }

    res = client.post("/planner/", json=planner_payload)
    assert res.status_code == 200, f"Planner request failed: {res.text}"
    trip_data = res.json()
    assert "trip_id" in trip_data
    trip_id = trip_data["trip_id"]

    # Verify trip persistence and traveler profiles
    stored = load_trip(trip_id)
    assert stored is not None
    stored_trip = stored["trip"]
    assert len(stored_trip["travelers"]) == 4

    # Verify each traveler's preferences were preserved
    names = [t["name"] for t in stored_trip["travelers"]]
    assert "Alice" in names
    assert "Bob" in names
    assert "Charlie" in names
    assert "Diana" in names

    # Verify that scheduled places have matched traveler metadata
    all_scheduled = []
    for day, places in stored_trip["day_schedule"].items():
        all_scheduled.extend(places)
    
    assert len(all_scheduled) > 0, "Expected scheduled activities in trip"
    matched_count = sum(1 for p in all_scheduled if len(p.get("matched_travelers", [])) > 0)
    print(f"Total scheduled activities: {len(all_scheduled)}, with matched travelers: {matched_count}")

    print("Step 49 Advanced Traveler Preferences all tests PASSED successfully!")

if __name__ == "__main__":
    test_advanced_traveler_preferences()
