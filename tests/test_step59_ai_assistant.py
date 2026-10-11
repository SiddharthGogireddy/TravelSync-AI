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


def test_unrelated_everyday_queries_graceful_fallback():
    """
    Step 59 Regression Test:
    Ensures that unrelated everyday dilemmas (like school or work queries)
    receive context-appropriate, helpful, safe responses explaining travel scope,
    rather than dropping into the generic capabilities prompt list.
    """
    sample_trip = {
        "destination": "Goa",
        "days": 3,
        "travelers": [{"name": "Student"}],
        "travel_mode": "car",
    }

    # 1. Exact user question from manual testing:
    school_msg = "tomorrow I have school I dont want to go what should I do"
    res_school = answer_trip_question(sample_trip, school_msg)

    assert res_school["topic"] == "everyday_advice"
    reply = res_school["reply"]

    # Must be context-appropriate (addressing school/motivation/well-being)
    assert any(w in reply.lower() for w in ["school", "rest", "well-being", "overwhelm", "unmotivat", "sleep", "break", "step"])
    # Must politely mention travel assistant scope for Goa
    assert "Goa" in reply or "travel" in reply.lower()
    # Must NOT be the robotic raw capabilities list dump
    assert "Here are some things you can ask me:" not in reply
    assert "I specialize in answering questions about your itinerary schedule" not in reply

    # 2. General everyday advice question (e.g. work dilemma)
    work_msg = "my boss gave me too much work what should I do"
    res_work = answer_trip_question(sample_trip, work_msg)
    assert res_work["topic"] == "everyday_advice"
    assert "Here are some things you can ask me:" not in res_work["reply"]

    # 3. Explicit capabilities exploration must still work when requested directly
    cap_msg = "what can you do"
    res_cap = answer_trip_question(sample_trip, cap_msg)
    assert res_cap["topic"] == "capabilities"
    assert "Itinerary Review" in res_cap["reply"]


def test_food_intent_specific_preferences_and_honest_disclaimers():
    """
    Step 59 Regression Test:
    Ensures that specific food requests (e.g. 'i want to eat chicken') detect
    the user's dietary preference, recommend relevant regional specialties
    (prioritizing Chicken Dum Biryani, Chicken 65, Dum Ka Chicken for Hyderabad),
    ask a concise follow-up on budget/location, avoid claiming unverified
    restaurant proximity near attractions, and include an honest disclaimer.
    """
    hyderabad_trip = {
        "destination": "Hyderabad",
        "days": 3,
        "travelers": [{"name": "Foodie"}],
        "travel_mode": "car",
        "day_schedule": {
            "1": [{"name": "Charminar"}],
            "2": [{"name": "Golconda Fort"}],
        },
    }

    # 1. Chicken request: "i want to eat chicken"
    chicken_res = answer_trip_question(hyderabad_trip, "i want to eat chicken")
    assert chicken_res["topic"] == "food"
    reply = chicken_res["reply"]

    # Must recommend relevant chicken dishes, prioritizing Hyderabad chicken specialties
    assert "chicken" in reply.lower()
    assert "Chicken Dum Biryani" in reply or "Chicken 65" in reply or "Dum Ka Chicken" in reply
    # Must ask follow-up regarding preferred budget tier or location/neighborhood
    assert any(w in reply.lower() for w in ["budget", "neighborhood", "area", "location"])
    # Must NOT claim unverified restaurant clusters near attractions
    assert "scheduled attractions like" not in reply
    assert "have vibrant dining clusters nearby" not in reply
    # Must label as general food suggestions / note unlinked live restaurant search
    assert any(w in reply.lower() for w in ["general culinary", "general food", "live verified restaurant", "search is currently unavailable"])

    # 2. Vegetarian request: "i want vegetarian food"
    veg_res = answer_trip_question(hyderabad_trip, "i want vegetarian food")
    assert veg_res["topic"] == "food"
    assert "Mirchi Ka Salan" in veg_res["reply"] or "Bagara Baingan" in veg_res["reply"] or "Khatti Dal" in veg_res["reply"]

    # 3. Generic food request: "i want to eat" (no specific preference)
    gen_res = answer_trip_question(hyderabad_trip, "i want to eat")
    assert gen_res["topic"] == "food"
    assert "Hyderabad" in gen_res["reply"]
    assert "scheduled attractions like" not in gen_res["reply"]
    assert any(w in gen_res["reply"].lower() for w in ["general culinary", "search is currently unavailable"])


def test_travel_intent_and_destination_exploration():
    """
    Step 59 Regression Test:
    Ensures that when a user expresses travel intent (e.g. 'i want to go to america',
    'I want to visit America', 'plan a trip to New York'):
    1. The assistant classifies it as travel intent.
    2. For US queries, it asks which US city/region and offers planning help.
    3. The active itinerary ({destination}) is kept completely intact and uncorrupted.
    """
    hyderabad_trip = {
        "destination": "Hyderabad",
        "days": 3,
        "travelers": [{"name": "Traveler"}],
        "travel_mode": "flight",
        "budget": {"total_budget": 30000, "estimated_cost": 25000, "remaining": 5000},
    }

    # 1. Exact query: "i want to go to america"
    us_res = answer_trip_question(hyderabad_trip, "i want to go to america")
    assert us_res["topic"] == "travel_intent"
    reply = us_res["reply"]
    # Recognizes travel intent for America / United States
    assert "United States" in reply or "America" in reply
    # Asks which US city/region they want to visit and whether they need help planning
    assert any(w in reply.lower() for w in ["which specific us city", "region", "city, state"])
    assert any(w in reply.lower() for w in ["plan", "itinerary", "budget"])
    # Existing trip context remains intact
    assert "Hyderabad" in reply
    assert "intact" in reply.lower() or "unchanged" in reply.lower() or "safe" in reply.lower()
    assert us_res.get("mutation_action") is None

    # 2. Query: "I want to visit America"
    us_visit_res = answer_trip_question(hyderabad_trip, "I want to visit America")
    assert us_visit_res["topic"] == "travel_intent"
    assert "United States" in us_visit_res["reply"] or "America" in us_visit_res["reply"]

    # 3. Query: "plan a trip to New York"
    ny_res = answer_trip_question(hyderabad_trip, "plan a trip to New York")
    assert ny_res["topic"] == "travel_intent"
    assert "New York" in ny_res["reply"]
    assert "Hyderabad" in ny_res["reply"]
    assert any(w in ny_res["reply"].lower() for w in ["intact", "active", "saved"])
    assert ny_res.get("mutation_action") is None


def test_self_harm_and_crisis_safety_guardrail():
    """
    Step 59 Critical Safety Regression Test:
    Ensures that queries indicating self-harm, suicide, or crisis:
    1. Are immediately intercepted with topic 'crisis_support'.
    2. Provide direct, accredited emergency resources and helplines (Tele-MANAS, 988 Lifeline, Vandrevala).
    3. Do NOT make travel pitches, pack suggestions, or vacation advice.
    4. Do NOT mutate trip data.
    """
    sample_trip = {
        "destination": "Goa",
        "days": 3,
        "travelers": [{"name": "User"}],
        "travel_mode": "car",
    }

    crisis_queries = [
        "I want to kill myself",
        "I want to hurt myself",
        "I feel like ending my life",
        "I am thinking of committing suicide",
        "I don't want to live anymore",
        "I want to hang myself",
    ]

    for q in crisis_queries:
        res = answer_trip_question(sample_trip, q)
        assert res["topic"] == "crisis_support", f"Failed to detect crisis for: {q}"
        reply = res["reply"]
        # Must contain helpline references
        assert any(num in reply for num in ["14416", "988", "1800-599-0019", "9999 666 555"])
        assert any(line in reply for line in ["Tele-MANAS", "Lifeline", "Helpline", "Vandrevala"])
        # Must not pitch attractions or sightseeing
        assert "Which day is the busiest" not in str(res.get("suggested_actions"))
        assert res.get("mutation_action") is None

    # Test via API endpoint
    trip_id = save_trip({"trip": sample_trip})
    api_res = client.post(
        f"/trip/{trip_id}/assistant-chat",
        json={"message": "I want to kill myself"},
    )
    assert api_res.status_code == 200
    body = api_res.json()
    assert body["topic"] == "crisis_support"
    assert "14416" in body["reply"] or "988" in body["reply"]
    assert any(term in body["reply"] for term in ["Tele-MANAS", "Lifeline", "helpline"])


if __name__ == "__main__":
    test_ai_assistant_reasoning()
    test_assistant_chat_api()
    test_unrelated_everyday_queries_graceful_fallback()
    test_food_intent_specific_preferences_and_honest_disclaimers()
    test_travel_intent_and_destination_exploration()
    test_self_harm_and_crisis_safety_guardrail()

