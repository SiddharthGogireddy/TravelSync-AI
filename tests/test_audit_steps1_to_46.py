import copy
import json
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip, update_saved_trip
from backend.services.storage.favorite_store import add_favorite, is_favorite, remove_favorite
from backend.services.storage.note_store import add_note, get_notes, delete_note
from backend.services.storage.rating_store import save_rating, get_rating
from backend.services.planner.distance import haversine
from backend.services.planner.travel_mode import get_mode_rules
from backend.services.planner.budget_tracker import calculate_budget
from backend.services.planner.opening_hours_scheduler import schedule_day_opening_hours
from backend.services.planner.meal_and_break_engine import plan_day_meals_and_breaks
from backend.services.trip_editor.prompt_parser import parse_prompt

client = TestClient(app)

SAMPLE_TRIP = {
    "trip": {
        "source": "Bengaluru, Karnataka, India",
        "destination": "Mysuru, Karnataka, India",
        "days": 2,
        "travel_mode": "car",
        "destination_location": {"lat": 12.2958, "lon": 76.6394},
        "travelers": [
            {
                "name": "Arun",
                "interests": ["Culture", "History"],
                "budget": "Medium",
                "pace": "Balanced",
            }
        ],
        "route": {
            "distance_km": 145.2,
            "duration_hours": 3.2,
        },
        "places": [
            {
                "name": "Mysore Palace",
                "lat": 12.3052,
                "lon": 76.6552,
                "category": "History",
                "estimated_spend": 200,
                "duration_minutes": 120,
            },
            {
                "name": "Chamundi Hills",
                "lat": 12.2753,
                "lon": 76.6705,
                "category": "Nature",
                "estimated_spend": 100,
                "duration_minutes": 90,
            },
        ],
        "hotels": [
            {
                "name": "Grand Mercure Mysuru",
                "rate": 3500,
                "lat": 12.3150,
                "lon": 76.6450,
            }
        ],
        "day_schedule": {
            "1": [
                {
                    "name": "Mysore Palace",
                    "lat": 12.3052,
                    "lon": 76.6552,
                    "category": "History",
                    "estimated_spend": 200,
                    "duration_minutes": 120,
                }
            ],
            "2": [
                {
                    "name": "Chamundi Hills",
                    "lat": 12.2753,
                    "lon": 76.6705,
                    "category": "Nature",
                    "estimated_spend": 100,
                    "duration_minutes": 90,
                }
            ],
        },
        "budget": {
            "total": 8500,
            "breakdown": {
                "transport": 2000,
                "hotels": 3500,
                "activities": 1000,
                "food": 1500,
                "emergency_fund": 500,
            },
        },
        "itinerary": {
            "days": [
                {
                    "day": 1,
                    "title": "Historical Immersion",
                    "activities": ["Visit Mysore Palace"],
                    "food": ["Traditional Thali"],
                    "budget": "4000",
                },
                {
                    "day": 2,
                    "title": "Scenic Exploration",
                    "activities": ["Hike up Chamundi Hills"],
                    "food": ["Filter Coffee and Mysore Pak"],
                    "budget": "4500",
                },
            ]
        },
    }
}


# ============================================================================
# Section A: Core Planning, Request Validation, Travel Modes, Budget, & Routes
# ============================================================================

def test_planner_request_validation_missing_fields():
    """Verify that omitting required fields results in 422 Unprocessable Entity."""
    # Missing source
    res = client.post("/planner/", json={
        "destination": "Goa",
        "days": 3,
        "travel_mode": "car",
        "travelers": [{"name": "Alex", "interests": ["Beaches"], "budget": "Medium", "pace": "Relaxed"}],
    })
    assert res.status_code == 422

    # Invalid travel_mode
    res = client.post("/planner/", json={
        "source": "Bengaluru",
        "destination": "Goa",
        "days": 3,
        "travel_mode": "spaceship",
        "travelers": [{"name": "Alex", "interests": ["Beaches"], "budget": "Medium", "pace": "Relaxed"}],
    })
    assert res.status_code == 422


def test_travel_mode_rules_and_metrics():
    """Verify travel mode rules for all 4 supported modes."""
    modes = ["car", "bus", "train", "flight"]
    for m in modes:
        rules = get_mode_rules(m)
        assert rules is not None
        assert "speed_kmh" in rules or "average_speed" in rules or "speed" in rules or len(rules) > 0


def test_distance_and_haversine_calculation():
    """Verify haversine formula accurately calculates geographical distance."""
    # Bengaluru (12.9716, 77.5946) to Mysuru (12.2958, 76.6394) is ~128 km straight line
    dist = haversine(12.9716, 77.5946, 12.2958, 76.6394)
    assert 120 < dist < 140

    # Same coordinate distance should be 0
    zero_dist = haversine(12.9716, 77.5946, 12.9716, 77.5946)
    assert zero_dist == 0.0


def test_budget_calculator_engine():
    """Verify calculate_budget computes comprehensive and positive total budgets."""
    places = [
        {"name": "Attraction 1", "estimated_spend": 300},
        {"name": "Attraction 2", "estimated_spend": 200},
    ]
    hotels = [{"rate": 2500}]
    travelers = [{"name": "Arun", "budget": "Medium"}]
    budget = calculate_budget(
        travelers=travelers,
        days=2,
        travel_mode="car",
        hotels=hotels,
        places=places,
    )
    assert budget["estimated_cost"] > 0
    categories = budget["categories"]
    assert "hotel" in categories
    assert "transport" in categories
    assert "activities" in categories


def test_opening_hours_and_meal_schedulers():
    """Verify opening hours scheduler and meal break scheduler organize daytime slots."""
    day_places = [
        {"name": "Museum", "duration_minutes": 120, "opening_hours": {"open": "09:00", "close": "18:00"}},
        {"name": "Fort", "duration_minutes": 90, "opening_hours": {"open": "10:00", "close": "17:00"}},
    ]
    scheduled, replan_notes = schedule_day_opening_hours(day_places, travel_mode="car", day_start_hour="09:00")
    assert isinstance(scheduled, list)
    assert len(scheduled) >= 2

    # Test meal break scheduling
    meals_plan = plan_day_meals_and_breaks(day_places=scheduled, available_places=[], day_index=1)
    assert isinstance(meals_plan, dict)
    assert "meals" in meals_plan
    assert len(meals_plan["meals"]) >= 1
    assert "rest_breaks" in meals_plan


# ============================================================================
# Section B: Natural-Language Trip Editing & Deterministic Fallbacks
# ============================================================================

def test_prompt_parser_deterministic_rules():
    """Verify regex/keyword parser accurately detects add, remove, budget, and day regeneration."""
    res_add = parse_prompt("Add Cubbon Park to day 1")
    assert "add_place" in res_add
    assert "cubbon park" in res_add["add_place"].lower()

    res_remove = parse_prompt("Remove Mysore Palace")
    assert "remove_place" in res_remove
    assert "mysore palace" in res_remove["remove_place"].lower()

    res_budget = parse_prompt("Change total budget to 12000")
    assert "budget" in res_budget
    assert res_budget["budget"] == 12000

    res_regen = parse_prompt("Regenerate day 2")
    assert "regenerate_day" in res_regen
    assert res_regen["regenerate_day"] == 2


def test_patch_trip_add_and_remove_place(isolated_storage, monkeypatch):
    """Test PATCH /trip/{id} adding and removing attractions."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    # Mock LLM interpreter to simulate prompt command
    def mock_interpret(prompt):
        if "add" in prompt.lower():
            return {"actions": [{"type": "add_place", "place": "Lalbagh"}]}
        if "remove" in prompt.lower():
            return {"actions": [{"type": "remove_place", "place": "Mysore Palace"}]}
        return {"actions": []}

    async def mock_find_place(name, lat, lon):
        return {
            "name": name,
            "kinds": "historic,monument",
            "dist": 1200,
            "point": {"lat": 12.30, "lon": 76.65},
        }

    monkeypatch.setattr("backend.routes.update_trip.interpret_trip_prompt", mock_interpret)
    monkeypatch.setattr("backend.routes.update_trip.find_place", mock_find_place)

    # 1. Add attraction via prompt
    res_add = client.patch(f"/trip/{trip_id}", json={"prompt": "Add Lalbagh"})
    assert res_add.status_code == 200
    updated_trip = load_trip(trip_id)
    all_place_names = [p["name"] for p in updated_trip["trip"].get("places", [])]
    assert any("lalbagh" in name.lower() for name in all_place_names)

    # 2. Remove attraction via direct payload
    res_remove = client.patch(f"/trip/{trip_id}", json={"remove_place": "Mysore Palace"})
    assert res_remove.status_code == 200
    updated_after_rem = load_trip(trip_id)
    remaining_names = [p["name"] for p in updated_after_rem["trip"].get("places", [])]
    assert not any("mysore palace" in name.lower() for name in remaining_names)


def test_patch_trip_llm_failure_graceful_fallback(isolated_storage, monkeypatch):
    """Test that when Gemini/LLM raises an error, PATCH safely falls back to deterministic parsing."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    def mock_failing_llm(prompt):
        raise RuntimeError("Quota exceeded 429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr("backend.routes.update_trip.interpret_trip_prompt", mock_failing_llm)

    res = client.patch(f"/trip/{trip_id}", json={"prompt": "Change budget to 9500"})
    assert res.status_code == 200
    updated = load_trip(trip_id)
    budget_obj = updated["trip"]["budget"]
    assert budget_obj.get("total_budget") == 9500 or budget_obj.get("total") == 9500


def test_patch_trip_not_found(isolated_storage):
    """Verify PATCH /trip/{nonexistent_id} returns 404."""
    res = client.patch("/trip/nonexistent-id-9999", json={"prompt": "Add Beach"})
    assert res.status_code == 404


# ============================================================================
# Section C: Persistence and Trip History Lifecycle
# ============================================================================

def test_persistence_lifecycle_and_history_sorting(isolated_storage):
    """Verify complete lifecycle: save trip -> retrieve -> list history (newest first) -> update."""
    import time

    # Save first trip
    trip1 = copy.deepcopy(SAMPLE_TRIP)
    trip1["trip"]["destination"] = "First Created City"
    id1 = save_trip(trip1)

    time.sleep(0.01)

    # Save second trip
    trip2 = copy.deepcopy(SAMPLE_TRIP)
    trip2["trip"]["destination"] = "Second Created City"
    id2 = save_trip(trip2)

    # Verify retrieval
    res_get1 = client.get(f"/trip/{id1}")
    assert res_get1.status_code == 200
    assert res_get1.json()["trip"]["destination"] == "First Created City"

    # Verify history ordering: newest (id2) should be first
    res_hist = client.get("/trip/history")
    assert res_hist.status_code == 200
    hist_trips = res_hist.json()["trips"]
    ids_in_order = [t["id"] for t in hist_trips]
    assert id2 in ids_in_order and id1 in ids_in_order
    assert ids_in_order.index(id2) < ids_in_order.index(id1)

    # Update first trip and verify it maintains original creation order
    trip1_loaded = load_trip(id1)
    trip1_loaded["trip"]["notes"] = ["Modified note"]
    update_saved_trip(id1, trip1_loaded)

    res_hist2 = client.get("/trip/history")
    hist_trips2 = res_hist2.json()["trips"]
    ids_after_update = [t["id"] for t in hist_trips2]
    assert ids_after_update.index(id2) < ids_after_update.index(id1)


def test_trip_history_and_view_regression_on_malformed_records(isolated_storage):
    """Verify that incomplete or legacy records do not crash /trip/history or /trip/{id}."""
    # Incomplete raw trip (missing destination_location, places, hotels, etc.)
    legacy_id = save_trip({
        "destination": "Legacy Ooty",
        "days": 2,
    })

    # History should render legacy record safely
    res_hist = client.get("/trip/history")
    assert res_hist.status_code == 200
    trips = res_hist.json()["trips"]
    found_legacy = next((t for t in trips if t["id"] == legacy_id), None)
    assert found_legacy is not None
    assert found_legacy["data"]["trip"]["destination"] == "Legacy Ooty"
    assert found_legacy["data"]["trip"]["destination_location"] is None

    # GET /trip/{id} should also return 200 without throwing AttributeError or KeyError
    res_view = client.get(f"/trip/{legacy_id}")
    assert res_view.status_code == 200


# ============================================================================
# Section D: Trip Features: Steps 36–46 (Export, Import, Duplicate, Compare, etc.)
# ============================================================================

def test_trip_export_and_import(isolated_storage):
    """Test exporting a trip as JSON and importing it back as a new trip."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    # 1. Export
    res_export = client.get(f"/trip/{trip_id}/export")
    assert res_export.status_code == 200
    exported_data = res_export.json()
    assert "trip" in exported_data or "destination" in exported_data

    # 2. Import
    res_import = client.post("/trip/import", json=exported_data)
    assert res_import.status_code == 200
    import_json = res_import.json()
    assert "trip_id" in import_json
    new_trip_id = import_json["trip_id"]
    assert new_trip_id != trip_id

    # Verify newly imported trip is retrievable
    res_new = client.get(f"/trip/{new_trip_id}")
    assert res_new.status_code == 200


def test_trip_duplication(isolated_storage):
    """Test POST /trip/{id}/duplicate creates a cloned trip with '(Copy)'."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    res_dup = client.post(f"/trip/{trip_id}/duplicate")
    assert res_dup.status_code == 200
    dup_data = res_dup.json()
    assert "trip_id" in dup_data
    dup_id = dup_data["trip_id"]
    assert dup_id != trip_id

    # Verify destination includes Copy or is cloned
    dup_record = load_trip(dup_id)
    assert dup_record is not None
    assert "copy" in dup_record["trip"]["destination"].lower() or dup_record["trip"]["destination"] == "Mysuru, Karnataka, India"


def test_trip_comparison(isolated_storage):
    """Test GET /trip/compare?trip1=...&trip2=..."""
    trip1 = copy.deepcopy(SAMPLE_TRIP)
    trip2 = copy.deepcopy(SAMPLE_TRIP)
    trip2["trip"]["destination"] = "Goa, India"
    trip2["trip"]["budget"]["total"] = 12000

    id1 = save_trip(trip1)
    id2 = save_trip(trip2)

    res = client.get(f"/trip/compare?trip1={id1}&trip2={id2}")
    assert res.status_code == 200
    data = res.json()
    assert "trip1" in data and "trip2" in data


def test_trip_insights(isolated_storage):
    """Test GET /trip/{id}/insights returns calculated analytics."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    res = client.get(f"/trip/{trip_id}/insights")
    assert res.status_code == 200
    insights = res.json()
    assert isinstance(insights, dict)
    assert len(insights) > 0


def test_favorites_crud(isolated_storage):
    """Test adding, checking, and removing trip favorites."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    # Check initially not favorite
    res_check = client.get(f"/trip/{trip_id}/favorite")
    assert res_check.status_code == 200
    assert res_check.json()["favorite"] is False

    # Add favorite
    res_add = client.post(f"/trip/{trip_id}/favorite")
    assert res_add.status_code == 200

    # Verify favorite
    res_check2 = client.get(f"/trip/{trip_id}/favorite")
    assert res_check2.json()["favorite"] is True

    # Remove favorite
    res_del = client.delete(f"/trip/{trip_id}/favorite")
    assert res_del.status_code == 200

    # Verify removed
    res_check3 = client.get(f"/trip/{trip_id}/favorite")
    assert res_check3.json()["favorite"] is False


def test_trip_notes_crud(isolated_storage):
    """Test adding, listing, and deleting trip notes and memories."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    # Add note
    res_add = client.post(f"/trip/{trip_id}/notes", json={"note": "Pack walking shoes for Chamundi Hills"})
    assert res_add.status_code == 200

    # Get notes
    res_get = client.get(f"/trip/{trip_id}/notes")
    assert res_get.status_code == 200
    notes = res_get.json()["notes"]
    assert len(notes) == 1
    assert "walking shoes" in notes[0]

    # Delete note
    res_del = client.delete(f"/trip/{trip_id}/notes/0")
    assert res_del.status_code == 200

    # Verify deleted
    res_get2 = client.get(f"/trip/{trip_id}/notes")
    assert len(res_get2.json()["notes"]) == 0


def test_trip_ratings_and_feedback(isolated_storage):
    """Test saving and retrieving trip ratings."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    # Save rating
    res_post = client.post(f"/trip/{trip_id}/rating", json={
        "rating": 5,
        "feedback": "Perfect historical itinerary!",
    })
    assert res_post.status_code == 200

    # Get rating
    res_get = client.get(f"/trip/{trip_id}/rating")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["rating"]["rating"] == 5
    assert "Perfect" in data["rating"]["feedback"]


# ============================================================================
# Section F: PDF Generation & Visual Robustness
# ============================================================================

def test_pdf_generation_content_and_headers(isolated_storage):
    """Verify PDF endpoint returns valid application/pdf binary content."""
    trip_id = save_trip(copy.deepcopy(SAMPLE_TRIP))

    res = client.get(f"/trip/{trip_id}/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000


def test_pdf_generation_with_unicode_and_special_chars(isolated_storage):
    """Verify PDF generator handles Unicode, accents, and special symbols safely."""
    unicode_trip = copy.deepcopy(SAMPLE_TRIP)
    unicode_trip["trip"]["destination"] = "München & Zürich — Rencontré"
    unicode_trip["trip"]["places"][0]["name"] = "Café de l'Opéra ★ Special"
    trip_id = save_trip(unicode_trip)

    res = client.get(f"/trip/{trip_id}/pdf")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


def test_pdf_generation_missing_optional_fields(isolated_storage):
    """Verify PDF generator safely handles trips with empty or missing optional fields."""
    sparse_trip = {
        "trip": {
            "source": "Origin",
            "destination": "Destination",
            "days": 1,
            "places": [],
            "hotels": [],
            "day_schedule": {"1": []},
        }
    }
    trip_id = save_trip(sparse_trip)

    res = client.get(f"/trip/{trip_id}/pdf")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


def test_pdf_generation_nonexistent_trip_returns_404(isolated_storage):
    """Verify PDF request for non-existent trip returns 404."""
    res = client.get("/trip/missing-trip-id/pdf")
    assert res.status_code == 404
