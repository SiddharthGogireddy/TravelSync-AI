import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.ai_assistant import answer_trip_question
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)

def test_ai_assistant_reasoning():
    print("Testing AI assistant reasoning logic...")
    sample_trip = {
        "destination": "Goa",
        "days": 3,
        "travelers": [{"name": "Siddharth", "budget": "moderate"}],
        "travel_mode": "car",
        "weather": [{"condition": "Light Rain", "temperature": 27}],
        "budget": {"total_budget": 25000, "estimated_cost": 22000, "remaining": 3000, "status": "Near Budget"},
        "day_schedule": {
            "1": [{"name": "Calangute Beach"}],
            "2": [{"name": "Aguada Fort"}],
        },
    }

    # 1. Test packing advice
    pack_res = answer_trip_question(sample_trip, "What should I pack for my trip?")
    assert pack_res["topic"] == "packing"
    assert "Goa" in pack_res["reply"]
    # Since rain was forecast, umbrella or waterproof should be included
    assert "umbrella" in pack_res["reply"].lower() or "waterproof" in pack_res["reply"].lower()
    assert len(pack_res["suggested_actions"]) > 0

    # 2. Test local food advice
    food_res = answer_trip_question(sample_trip, "What are the best local dishes to try?")
    assert food_res["topic"] == "food"
    assert "Goa" in food_res["reply"]
    assert "Fish Curry" in food_res["reply"] or "Cafreal" in food_res["reply"] or "Bebinca" in food_res["reply"]

    # 3. Test timing advice
    timing_res = answer_trip_question(sample_trip, "When is the best time for sunset and timing?")
    assert timing_res["topic"] == "timing"
    assert "Sunset" in timing_res["reply"]

    # 4. Test safety & etiquette
    safety_res = answer_trip_question(sample_trip, "Any safety or cultural etiquette tips?")
    assert safety_res["topic"] == "etiquette"
    assert "Etiquette" in safety_res["reply"] or "Safety" in safety_res["reply"]
    print("ai_assistant_reasoning OK!")


def test_assistant_chat_api():
    print("Testing POST /trip/{trip_id}/assistant-chat API endpoint...")
    trip_data = {
        "destination": "Bengaluru",
        "days": 2,
        "travelers": [{"name": "Alex"}],
        "travel_mode": "train",
        "weather": [{"condition": "Pleasant", "temperature": 24}],
        "budget": {"total_budget": 15000, "estimated_cost": 12000, "remaining": 3000, "status": "Under Budget"},
        "day_schedule": {
            "1": [{"name": "Cubbon Park"}],
        },
        "assistant_history": [],
    }
    trip_id = save_trip({"trip": trip_data})

    res = client.post(
        f"/trip/{trip_id}/assistant-chat",
        json={"message": "Can you recommend top regional foods to eat in Bengaluru?"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert "reply" in body
    assert "Dosa" in body["reply"] or "Coffee" in body["reply"] or "Bengaluru" in body["reply"]
    assert len(body["suggested_actions"]) > 0

    # Verify history is stored
    saved = load_trip(trip_id)
    assert saved is not None
    history = saved["trip"].get("assistant_history", [])
    assert len(history) == 2  # user + assistant
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    print("Step 59 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_ai_assistant_reasoning()
    test_assistant_chat_api()
