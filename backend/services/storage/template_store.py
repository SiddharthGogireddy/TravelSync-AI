import copy
import json
import os
import uuid
from datetime import datetime, timezone
from backend.services.storage.trip_store import load_trip, save_trip

FILE = "backend/data/templates.json"


def _ensure_store_file():
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    if not os.path.exists(FILE):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


def load_all_templates() -> list:
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_all_templates(templates: list):
    _ensure_store_file()
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2)


def get_template(template_id: str) -> dict | None:
    templates = load_all_templates()
    for tpl in templates:
        if tpl.get("id") == template_id:
            return tpl
    return None


def extract_template_metadata(trip_data: dict) -> dict:
    """
    Extracts key planning information from saved trip data for reusable templating:
    destination, duration, travel mode, traveler preferences, and itinerary structure.
    """
    trip = trip_data.get("trip", {}) if isinstance(trip_data, dict) else {}
    
    destination = trip.get("destination", "Unknown Destination")
    source = trip.get("source", "Unknown Origin")
    duration_days = int(trip.get("days", 1))
    travel_mode = trip.get("travel_mode", "car")
    
    # Extract unique traveler preferences / interests
    preferences = []
    travelers = trip.get("travelers", [])
    if isinstance(travelers, list):
        for tr in travelers:
            if isinstance(tr, dict):
                interests = tr.get("interests", [])
                if isinstance(interests, list):
                    for item in interests:
                        if isinstance(item, str) and item.strip() and item.strip().lower() not in [p.lower() for p in preferences]:
                            preferences.append(item.strip())
                elif isinstance(interests, str) and interests.strip():
                    if interests.strip().lower() not in [p.lower() for p in preferences]:
                        preferences.append(interests.strip())

    # Structure day-by-day outline
    day_schedule = trip.get("day_schedule", {})
    places = trip.get("places", [])
    hotels = trip.get("hotels", [])
    mandatory_visits = trip.get("mandatory_visits", [])
    budget = trip.get("budget", {})
    route = trip.get("route", {})

    itinerary_structure = {
        "days_count": duration_days,
        "places_count": len(places) if isinstance(places, list) else 0,
        "hotels_count": len(hotels) if isinstance(hotels, list) else 0,
        "mandatory_visits": mandatory_visits if isinstance(mandatory_visits, list) else [],
        "places_summary": [
            {
                "name": p.get("name", "Unknown Place"),
                "category": p.get("category", "General"),
                "duration_hours": p.get("duration_hours", 2),
            }
            for p in (places[:10] if isinstance(places, list) else [])
        ],
        "schedule_outline": {
            str(day): len(acts) if isinstance(acts, list) else 0
            for day, acts in (day_schedule.items() if isinstance(day_schedule, dict) else [])
        },
    }

    return {
        "destination": destination,
        "source": source,
        "duration_days": duration_days,
        "travel_mode": travel_mode,
        "preferences": preferences,
        "budget_summary": {
            "total_budget": budget.get("total_budget", 0) if isinstance(budget, dict) else 0,
            "estimated_cost": budget.get("estimated_cost", 0) if isinstance(budget, dict) else 0,
        },
        "route_summary": {
            "distance_km": route.get("distance_km", 0) if isinstance(route, dict) else 0,
            "duration_hr": route.get("duration_hr", "N/A") if isinstance(route, dict) else "N/A",
        },
        "itinerary_structure": itinerary_structure,
    }


def save_template_from_trip(
    trip_id: str,
    name: str = "",
    description: str = "",
    category: str = "General",
) -> dict:
    original_trip = load_trip(trip_id)
    if not original_trip:
        raise ValueError(f"Trip with ID {trip_id} not found")

    meta = extract_template_metadata(original_trip)
    
    clean_name = name.strip() if name and name.strip() else f"{meta['duration_days']}-Day {meta['destination']} Itinerary"
    clean_desc = description.strip() if description and description.strip() else f"Reusable template based on {meta['destination']} trip ({meta['travel_mode'].capitalize()})"

    template_id = f"tpl_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Deep copy the complete planning data snapshot so it can be fully reconstructed
    snapshot_payload = copy.deepcopy(original_trip)

    template = {
        "id": template_id,
        "name": clean_name,
        "description": clean_desc,
        "category": category.strip() if category else "General",
        "source_trip_id": trip_id,
        "created_at": now_iso,
        "destination": meta["destination"],
        "source": meta["source"],
        "duration_days": meta["duration_days"],
        "travel_mode": meta["travel_mode"],
        "preferences": meta["preferences"],
        "budget_summary": meta["budget_summary"],
        "route_summary": meta["route_summary"],
        "itinerary_structure": meta["itinerary_structure"],
        "template_data": snapshot_payload,
    }

    templates = load_all_templates()
    templates.insert(0, template)
    _save_all_templates(templates)

    return template


def create_trip_from_template(template_id: str, overrides: dict = None) -> tuple[str, dict]:
    """
    Creates a new trip from a template.
    Does NOT mutate the original template or the original source trip.
    """
    template = get_template(template_id)
    if not template:
        raise ValueError(f"Template with ID {template_id} not found")

    overrides = overrides or {}

    # Deep copy the snapshot payload so neither template nor source trip is affected
    new_trip_payload = copy.deepcopy(template.get("template_data", {}))

    trip_obj = new_trip_payload.get("trip", {})
    if not isinstance(trip_obj, dict):
        trip_obj = {}
        new_trip_payload["trip"] = trip_obj

    # Apply optional user overrides (e.g., custom source, custom travel mode, custom budget)
    if "source" in overrides and overrides["source"]:
        trip_obj["source"] = str(overrides["source"]).strip()
    if "travel_mode" in overrides and overrides["travel_mode"]:
        trip_obj["travel_mode"] = str(overrides["travel_mode"]).strip()
    if "budget" in overrides and isinstance(overrides["budget"], (int, float)):
        if "budget" in trip_obj and isinstance(trip_obj["budget"], dict):
            trip_obj["budget"]["total_budget"] = float(overrides["budget"])

    # Update metadata to show it was spawned from a template
    trip_obj["spawned_from_template"] = {
        "template_id": template_id,
        "template_name": template.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save as a brand new independent trip
    new_trip_id = save_trip(new_trip_payload)

    return new_trip_id, new_trip_payload


def delete_template(template_id: str) -> bool:
    templates = load_all_templates()
    initial_len = len(templates)
    updated = [t for t in templates if t.get("id") != template_id]
    if len(updated) != initial_len:
        _save_all_templates(updated)
        return True
    return False
