import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip
from backend.services.planner.route_attractions import (
    discover_route_attractions,
    insert_route_stop_into_day,
)
from backend.services.planner.budget_tracker import calculate_budget
from backend.services.planner.budget_reallocator import apply_budget_reallocation
from backend.services.planner.transport_recommendation_engine import switch_trip_transport
from backend.services.planner.group_decision_engine import (
    evaluate_group_decisions,
    cast_group_vote,
    resolve_group_conflicts,
)
from backend.services.planner.ai_assistant import answer_trip_question
from backend.services.planner.ai_trip_optimizer import (
    optimize_trip_itinerary,
    calculate_trip_optimization_score,
)

client = TestClient(app)


def test_step55_route_attractions_evaluation_and_duplicates():
    # 1. Test discover_route_attractions with day_schedule
    route_obj = {
        "routes": [{
            "geometry": {
                "coordinates": [
                    [77.5946, 12.9716],
                    [76.6394, 12.2958],
                ]
            }
        }]
    }
    day_schedule = {
        "1": [
            {"name": "Bangalore Palace", "lat": 12.9988, "lon": 77.5921},
            {"name": "Cubbon Park", "lat": 12.9763, "lon": 77.5929},
        ],
        "2": [
            {"name": "Mysore Palace", "lat": 12.3052, "lon": 76.6552},
        ],
    }

    discovered = asyncio.run(discover_route_attractions(
        route=route_obj,
        destination_places=[],
        travel_mode="car",
        max_detour_km=40.0,
        day_schedule=day_schedule,
    ))

    assert len(discovered) > 0
    first_stop = discovered[0]
    assert "recommended_day" in first_stop
    assert "day_evaluations" in first_stop
    assert "1" in first_stop["day_evaluations"] or "2" in first_stop["day_evaluations"]

    eval_data = list(first_stop["day_evaluations"].values())[0]
    assert "straight_line_distance_km" in eval_data
    assert "estimated_road_distance_km" in eval_data
    assert "detour_distance_km" in eval_data
    assert "total_daily_route_km" in eval_data
    assert "has_schedule_capacity" in eval_data

    # 2. Test duplicate stop prevention & allow_repeat flag
    sample_trip = {
        "destination": "Bengaluru",
        "day_schedule": {
            "1": [
                {"name": "Cubbon Park", "travel_time_minutes": 20},
            ]
        }
    }
    duplicate_stop = {
        "name": "Cubbon Park",
        "detour_distance_km": 0.0,
        "added_travel_time_minutes": 0,
        "recommended_pause_minutes": 30,
    }

    # Should be rejected when allow_repeat is False
    res_rejected, audit_rejected = insert_route_stop_into_day(
        trip_data=sample_trip,
        day_number=1,
        route_stop=duplicate_stop,
        allow_repeat=False,
    )
    assert audit_rejected["is_duplicate"] is True
    assert len(res_rejected["day_schedule"]["1"]) == 1

    # Should be accepted when allow_repeat is True
    res_allowed, audit_allowed = insert_route_stop_into_day(
        trip_data=sample_trip,
        day_number=1,
        route_stop=duplicate_stop,
        allow_repeat=True,
    )
    assert audit_allowed["success"] is True
    assert res_allowed["day_schedule"]["1"][1].get("is_repeat_stop") is True or res_allowed["day_schedule"]["1"][1].get("is_repeat") is True


def test_step56_transport_switch_budget_and_dashboard_sync():
    sample_trip = {
        "source": "Bengaluru",
        "destination": "Goa",
        "travel_mode": "car",
        "days": 3,
        "route": {"distance_km": 580.0, "duration_hours": 10.0},
        "travelers": [{"name": "Traveler 1", "budget": 20000}],
        "budget": {
            "categories": {"hotel": 9000, "food": 4500, "transport": 5800, "activities": 3000, "emergency": 2230},
            "total_budget": 24530,
            "estimated_cost": 24530,
            "remaining": 0,
            "status": "Balanced",
        },
        "day_schedule": {
            "1": [{"name": "Stop 1", "estimated_cost": 500}],
            "2": [{"name": "Stop 2", "estimated_cost": 500}],
            "3": [{"name": "Stop 3", "estimated_cost": 500}],
        },
        "dashboard": {
            "travel_mode": "car",
            "destination": "Goa",
            "days": 3,
            "total_budget": 24530,
            "estimated_cost": 24530,
        },
    }
    trip_id = save_trip({"trip": sample_trip, "dashboard": sample_trip["dashboard"]})

    res = client.post(
        f"/trip/{trip_id}/switch-transport",
        json={"travel_mode": "flight"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    updated_trip = body["trip"]

    # Verify transport cost updated and dashboard synchronized
    flight_transport_cost = updated_trip["budget"]["categories"]["transport"]
    assert flight_transport_cost > 0
    assert updated_trip["travel_mode"] == "flight"
    assert updated_trip["dashboard"]["travel_mode"] == "flight"
    assert updated_trip["dashboard"]["estimated_cost"] == updated_trip["budget"]["estimated_cost"]


def test_step57_budget_single_source_of_truth_and_no_activity_inflation():
    # 70 candidate places pool (simulating raw places pool from OpenTripMap)
    candidate_places = [{"name": f"Place {i}", "cost": 1500} for i in range(70)]
    day_schedule = {
        "1": [{"name": "Place 0", "cost": 1500}, {"name": "Place 1", "cost": 1500}],
        "2": [{"name": "Place 2", "cost": 1500}, {"name": "Place 3", "cost": 1500}],
    }

    # calculate_budget should NOT multiply 70 by 1500 (which would be 105k)
    # It must respect day_schedule (4 stops)
    budget = calculate_budget(
        travelers=[{"name": "Alice"}],
        places=candidate_places,
        hotels=[],
        days=2,
        travel_mode="car",
    )
    assert budget["categories"]["activities"] < 30000  # realistic activities budget
    # Initial budget without explicit total_budget must NOT be perpetually negative/Over Budget
    assert budget["remaining"] >= 0
    assert budget["status"] in ["Balanced", "Under Budget", "Near Budget"]
    assert budget["status"] != "Over Budget"
    assert budget["total_budget"] == budget["estimated_cost"]

    # Test reallocator synchronization
    sample_trip = {
        "destination": "Mysuru",
        "days": 2,
        "travelers": [{"name": "Alex", "budget": 15000}],
        "budget": budget,
        "day_schedule": day_schedule,
        "dashboard": {
            "total_budget": budget["total_budget"],
            "estimated_cost": budget["estimated_cost"],
        },
    }
    reallocated_trip, audit = apply_budget_reallocation(sample_trip, strategy="conservative")
    assert audit["success"] is True
    assert "average_per_day" in reallocated_trip["budget"]
    assert "average_per_person" in reallocated_trip["budget"]
    assert "budget_utilization_pct" in reallocated_trip["budget"]
    assert reallocated_trip["dashboard"]["estimated_cost"] == reallocated_trip["budget"]["estimated_cost"]


def test_step58_group_decision_conflict_detection_and_resolution():
    sample_trip = {
        "travelers": [
            {"name": "Alice", "interests": ["nature"]},
            {"name": "Bob", "interests": ["nightlife"]},
        ],
        "places": [
            {"name": "Nightclub Central", "category": "Nightlife"},
            {"name": "Botanical Sanctuary", "category": "Nature"},
        ],
        "day_schedule": {
            "1": [
                {"name": "Nightclub Central", "category": "Nightlife", "travel_time_minutes": 15},
            ]
        },
        "group_votes": {
            "Nightclub Central": {
                "Bob": "up",
                "Alice": "down",
            }
        },
        "budget": {
            "total_budget": 20000,
            "estimated_cost": 18000,
            "remaining": 2000,
            "status": "Balanced",
            "categories": {"hotel": 8000, "food": 5000, "transport": 3000, "activities": 2000, "emergency": 0},
        },
        "dashboard": {},
    }

    # Conflict evaluation should detect split preference
    eval_result = evaluate_group_decisions(sample_trip)
    assert "detected_conflicts" in eval_result
    assert len(eval_result["detected_conflicts"]) >= 1
    conflict = eval_result["detected_conflicts"][0]
    assert conflict["place_name"] == "Nightclub Central"
    assert conflict["conflict_type"] == "split_preference"
    assert "proposed_resolution" in conflict

    # Conflict resolution should apply split compromise and record in applied_resolutions
    resolved_trip, res_audit = resolve_group_conflicts(sample_trip)
    assert res_audit["success"] is True
    assert len(resolved_trip["group_decisions"]["applied_resolutions"]) >= 1
    applied = resolved_trip["group_decisions"]["applied_resolutions"][0]
    assert applied["attraction"] == "Nightclub Central"
    assert applied["strategy"] == "split_compromise"
    assert "dashboard" in resolved_trip


def test_step59_ai_assistant_intent_reasoning_and_mutation():
    sample_trip = {
        "destination": "Goa",
        "days": 2,
        "travelers": [{"name": "Siddharth"}],
        "travel_mode": "car",
        "day_schedule": {
            "1": [
                {"name": "Anjuna Beach", "travel_time_minutes": 15, "estimated_cost": 500},
                {"name": "Water Sports Arena", "travel_time_minutes": 25, "estimated_cost": 3500},
            ],
            "2": [
                {"name": "Old Goa Churches", "travel_time_minutes": 10, "estimated_cost": 200},
            ],
        },
        "places": [
            {"name": "Reis Magos Fort", "estimated_cost": 300, "category": "Heritage"},
        ],
        "budget": {
            "total_budget": 15000,
            "estimated_cost": 14000,
            "remaining": 1000,
            "status": "Balanced",
            "categories": {"hotel": 6000, "food": 3800, "transport": 2000, "activities": 2200, "emergency": 0},
        },
        "weather": [
            {"day": 1, "temperature": 34.0, "condition": "Sunny"},
            {"day": 2, "temperature": 27.5, "condition": "Breezy"},
        ],
        "dashboard": {},
    }

    # 1. Test busiest day calculation
    busiest_res = answer_trip_question(sample_trip, "Which day is the busiest?")
    assert busiest_res["topic"] in ["itinerary", "schedule"]
    assert "Day 1" in busiest_res["reply"]

    # 1b. Test hottest and coldest day comparison
    weather_res = answer_trip_question(sample_trip, "Which day is hottest and coldest?")
    assert weather_res["topic"] == "weather"
    assert "Day 1" in weather_res["reply"]  # 34C hottest
    assert "Day 2" in weather_res["reply"]  # 27.5C coldest
    assert "busiest" not in weather_res["reply"].lower()

    # 1c. Test heat advice
    heat_res = answer_trip_question(sample_trip, "Today is so hot, what should I do?")
    assert heat_res["topic"] == "weather_advice"
    assert any(w in heat_res["reply"].lower() for w in ["hydrate", "sun", "indoor", "water"])

    # 1d. Test food request (general)
    food_res = answer_trip_question(sample_trip, "I want to eat")
    assert food_res["topic"] == "food"
    assert len(food_res["reply"]) > 20
    assert "scheduled attractions like" not in food_res["reply"]

    # 1d-2. Test chicken-specific food request for Hyderabad trip
    hyd_trip = dict(sample_trip, destination="Hyderabad")
    chicken_res = answer_trip_question(hyd_trip, "i want to eat chicken")
    assert chicken_res["topic"] == "food"
    assert "chicken" in chicken_res["reply"].lower()
    assert any(dish in chicken_res["reply"] for dish in ["Chicken Dum Biryani", "Chicken 65", "Dum Ka Chicken"])
    assert any(term in chicken_res["reply"].lower() for term in ["budget", "neighborhood", "area", "location"])
    assert "scheduled attractions like" not in chicken_res["reply"]
    assert any(term in chicken_res["reply"].lower() for term in ["general culinary", "search is currently unavailable"])

    # 1d-3. Test vegetarian preference
    veg_res = answer_trip_question(hyd_trip, "i want to eat veg")
    assert veg_res["topic"] == "food"
    assert any(dish in veg_res["reply"] for dish in ["Mirchi Ka Salan", "Bagara Baingan", "Khatti Dal"])

    # 1e. Test greeting
    greeting_res = answer_trip_question(sample_trip, "Hello!")
    assert greeting_res["topic"] == "greeting"
    hi_res = answer_trip_question(sample_trip, "hi")
    assert hi_res["topic"] == "greeting"

    # 1f. Test everyday out-of-domain query (school question)
    school_res = answer_trip_question(sample_trip, "tomorrow I have school I dont want to go what should I do")
    assert school_res["topic"] == "everyday_advice"
    assert "Here are some things you can ask me:" not in school_res["reply"]
    assert any(w in school_res["reply"].lower() for w in ["school", "rest", "well-being", "overwhelm", "unmotivat", "sleep", "break", "step"])
    assert "Goa" in school_res["reply"] or "travel" in school_res["reply"].lower()

    # 1g. Test travel intent queries
    # "i want to go to america"
    us_intent_1 = answer_trip_question(hyd_trip, "i want to go to america")
    assert us_intent_1["topic"] == "travel_intent"
    assert "United States" in us_intent_1["reply"] or "America" in us_intent_1["reply"]
    assert any(term in us_intent_1["reply"].lower() for term in ["city", "region"])
    assert any(term in us_intent_1["reply"].lower() for term in ["plan", "itinerary", "budget"])
    assert "Hyderabad" in us_intent_1["reply"]
    assert us_intent_1.get("mutation_action") is None

    # "I want to visit America"
    us_intent_2 = answer_trip_question(hyd_trip, "I want to visit America")
    assert us_intent_2["topic"] == "travel_intent"
    assert "United States" in us_intent_2["reply"] or "America" in us_intent_2["reply"]

    # "plan a trip to New York"
    ny_intent = answer_trip_question(hyd_trip, "plan a trip to New York")
    assert ny_intent["topic"] == "travel_intent"
    assert "New York" in ny_intent["reply"]
    assert "Hyderabad" in ny_intent["reply"]
    assert ny_intent.get("mutation_action") is None

    # 1h. Test critical self-harm safety guardrail
    crisis_res = answer_trip_question(sample_trip, "I want to kill myself")
    assert crisis_res["topic"] == "crisis_support"
    assert any(num in crisis_res["reply"] for num in ["14416", "988", "1800-599-0019", "9999 666 555"])
    assert any(line in crisis_res["reply"] for line in ["Tele-MANAS", "Lifeline", "Helpline"])
    assert crisis_res.get("mutation_action") is None
    assert "Which day is the busiest" not in str(crisis_res.get("suggested_actions"))

    # 2. Test replacing most expensive attraction
    replace_res = answer_trip_question(sample_trip, "Replace the most expensive attraction with a cheaper one")
    assert replace_res["topic"] == "modification"
    assert "mutation_action" in replace_res
    mutation = replace_res["mutation_action"]
    assert mutation["action"] == "replace_attraction"
    assert mutation["old_attraction"] == "Water Sports Arena"
    assert mutation["new_attraction"] == "Reis Magos Fort"
    assert "updated_trip" in mutation

    # 3. Test API endpoint applies mutation directly to stored trip
    trip_id = save_trip({"trip": sample_trip})
    api_res = client.post(
        f"/trip/{trip_id}/assistant-chat",
        json={"message": "Replace the most expensive attraction with a cheaper one"},
    )
    assert api_res.status_code == 200
    api_body = api_res.json()
    assert api_body["success"] is True
    assert "trip" in api_body
    # Water Sports Arena should be gone from Day 1
    day1_names = [p["name"] for p in api_body["trip"]["day_schedule"]["1"]]
    assert "Water Sports Arena" not in day1_names
    assert "Reis Magos Fort" in day1_names


def test_step60_ai_trip_optimizer_comparison_and_honest_metrics():
    sample_trip = {
        "source": "Bengaluru",
        "destination": "Mysuru",
        "duration": 1,
        "travel_mode": "car",
        "travelers": [{"name": "User", "budget": 10000}],
        "budget": {
            "total_budget": 10000,
            "status": "Balanced",
            "remaining": 1000,
            "categories": {"stay": 5000, "food": 2500, "activities": 1500, "buffer": 1000},
        },
        "day_schedule": {
            "1": [
                {
                    "name": "Point A",
                    "lat": 12.30,
                    "lon": 76.65,
                    "travel_from_previous_km": 0.0,
                    "travel_time_minutes": 0,
                },
                {
                    "name": "Point C (Far away)",
                    "lat": 12.45,
                    "lon": 76.55,
                    "travel_from_previous_km": 25.0,
                    "travel_time_minutes": 45,
                },
                {
                    "name": "Point B (Close to A)",
                    "lat": 12.31,
                    "lon": 76.66,
                    "travel_from_previous_km": 24.5,
                    "travel_time_minutes": 44,
                },
            ]
        },
        "dashboard": {},
    }

    optimized_trip, audit = optimize_trip_itinerary(sample_trip)
    assert audit["success"] is True
    assert "comparison" in audit
    comparison = audit["comparison"]
    assert "initial_score" in comparison
    assert "optimized_score" in comparison
    assert "distance_saved_km" in comparison
    assert "transit_minutes_saved" in comparison
    assert "day_changes" in comparison

    # Day 1 should have been reordered: A -> B -> C instead of A -> C -> B
    day1_order = [p["name"] for p in optimized_trip["day_schedule"]["1"]]
    assert day1_order == ["Point A", "Point B (Close to A)", "Point C (Far away)"]
    assert comparison["distance_saved_km"] > 0

    # Ensure original_itinerary_snapshot is preserved for auditing
    assert "original_itinerary_snapshot" in optimized_trip
    assert "dashboard" in optimized_trip


def test_step60_corridor_itinerary_optimization_and_metric_consistency():
    """
    Step 60 Regression Test:
    Validates optimization of the corridor itinerary:
    Day 1 initial:
      Ancient Rock-Cut Caves -> Riverside Waterfall Rest Area -> Scenic Valley Viewpoint -> Highway Heritage Dhaba & Tea Garden
    Day 1 optimized:
      Ancient Rock-Cut Caves -> Riverside Waterfall Rest Area -> Highway Heritage Dhaba & Tea Garden -> Scenic Valley Viewpoint

    Verifies:
    1. Distance savings of 80 km (415 km -> 335 km) from actual route legs.
    2. Both before and after metrics use consistent leg measurements.
    3. Missing coordinates or failed routing are not treated as zero distance or zero time.
    4. Day boundaries and stops are fully preserved without drops or swaps across days.
    5. Re-running optimization is idempotent (0 additional savings, 0 score inflation).
    """
    corridor_trip = {
        "source": "Hyderabad, Telangana, India",
        "destination": "Bengaluru, Karnataka, India",
        "travel_mode": "car",
        "travelers": [{"name": "Explorer"}],
        "budget": {"total_budget": 25000, "estimated_cost": 20000, "remaining": 5000, "status": "Under Budget"},
        "day_schedule": {
            "1": [
                {
                    "name": "Ancient Rock-Cut Caves",
                    "lat": 15.3173,
                    "lon": 77.8614,
                    "travel_from_previous_km": 0.0,
                    "travel_time_minutes": 0,
                },
                {
                    "name": "Riverside Waterfall Rest Area",
                    "lat": 14.6766,
                    "lon": 77.5834,
                    "travel_from_previous_km": 77.2,
                    "travel_time_minutes": 138,
                },
                {
                    "name": "Scenic Valley Viewpoint",
                    "lat": 16.9125,
                    "lon": 78.1702,
                    "travel_from_previous_km": 256.4,
                    "travel_time_minutes": 445,
                },
                {
                    "name": "Highway Heritage Dhaba & Tea Garden",
                    "lat": 16.2059,
                    "lon": 78.0193,
                    "travel_from_previous_km": 80.2,
                    "travel_time_minutes": 143,
                },
            ],
            "2": [
                {"name": "Stop 2A", "lat": 12.9775, "lon": 77.5880, "travel_from_previous_km": 0.0, "travel_time_minutes": 0},
                {"name": "Stop 2B", "lat": 12.9789, "lon": 77.5881, "travel_from_previous_km": 0.2, "travel_time_minutes": 10},
                {"name": "Stop 2C", "lat": 12.9789, "lon": 77.5889, "travel_from_previous_km": 0.1, "travel_time_minutes": 10},
                {"name": "Stop 2D", "lat": 12.9802, "lon": 77.5901, "travel_from_previous_km": 0.2, "travel_time_minutes": 10},
            ],
            "3": [
                {"name": "Stop 3A", "lat": 12.9762, "lon": 77.5872, "travel_from_previous_km": 0.0, "travel_time_minutes": 0},
                {"name": "Stop 3B", "lat": 12.9741, "lon": 77.5880, "travel_from_previous_km": 0.2, "travel_time_minutes": 10},
                {"name": "Stop 3C", "lat": 12.9735, "lon": 77.5903, "travel_from_previous_km": 0.3, "travel_time_minutes": 10},
                {"name": "Stop 3D", "lat": 12.9742, "lon": 77.5922, "travel_from_previous_km": 0.2, "travel_time_minutes": 10},
            ],
        },
        "dashboard": {},
    }

    # 1. Run optimization
    opt_trip, audit = optimize_trip_itinerary(corridor_trip)
    assert audit["success"] is True

    comp = audit["comparison"]
    # Check reported distance: 415 km -> 335 km (80 km saved)
    assert comp["initial_total_transit_km"] == 415.0
    assert comp["optimized_total_transit_km"] == 335.0
    assert comp["distance_saved_km"] == 80.0
    assert comp["transit_minutes_saved"] > 0

    # Verify Day 1 ordering: Caves -> Waterfall -> Dhaba -> Viewpoint
    day1_names = [p["name"] for p in opt_trip["day_schedule"]["1"]]
    assert day1_names == [
        "Ancient Rock-Cut Caves",
        "Riverside Waterfall Rest Area",
        "Highway Heritage Dhaba & Tea Garden",
        "Scenic Valley Viewpoint",
    ]

    # Verify Day 2 and Day 3 preserve all stops and order
    assert len(opt_trip["day_schedule"]["2"]) == 4
    assert len(opt_trip["day_schedule"]["3"]) == 4

    # 2. Test idempotence: re-running optimization produces 0 additional savings
    rerun_trip, rerun_audit = optimize_trip_itinerary(opt_trip)
    assert rerun_audit["saved_distance_km"] == 0.0
    assert rerun_audit["saved_transit_minutes"] == 0
    assert rerun_audit["score_improvement"] == 0
    assert rerun_audit["days_optimized"] == 0

    # 3. Test missing coordinates robustness: never treated as zero distance or time
    missing_coords_trip = {
        "travel_mode": "car",
        "day_schedule": {
            "1": [
                {"name": "Start", "lat": 12.0, "lon": 77.0},
                {"name": "Unknown Point", "lat": None, "lon": None, "travel_from_previous_km": None, "travel_time_minutes": None},
            ]
        }
    }
    score = calculate_trip_optimization_score(missing_coords_trip)
    assert score["stats"]["total_transit_km"] > 0
    assert score["stats"]["total_transit_minutes"] >= 10
