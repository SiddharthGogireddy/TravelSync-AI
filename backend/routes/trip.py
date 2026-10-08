import copy
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, Body
from fastapi.responses import FileResponse

from backend.services.expense.expense_store import get_expenses, add_expense
from backend.services.storage.favorite_store import (
    add_favorite,
    remove_favorite,
    is_favorite,
)
from backend.services.storage.note_store import (
    get_notes,
    add_note,
    delete_note,
)
from backend.services.storage.rating_store import (
    get_rating,
    save_rating,
)
from backend.services.storage.trip_store import (
    load_trip,
    save_trip,
    update_saved_trip,
    load_all_trips,
)

router = APIRouter(
    prefix="/trip",
    tags=["Trip"]
)


@router.get("/history")
def get_trip_history():
    trips = load_all_trips()

    return {
        "trips": trips
    }


def extract_comparison_metrics(trip_wrapper: dict, trip_id: str) -> dict:
    trip = trip_wrapper.get("trip", {})
    route = trip.get("route", {})
    budget = trip.get("budget", {})
    travelers = trip.get("travelers", [])
    hotels = trip.get("hotels", [])
    places = trip.get("places", [])
    weather = trip.get("weather", [])

    total_dist = route.get("distance_km")
    if total_dist is None or not isinstance(total_dist, (int, float)):
        total_dist = 0.0

    total_budget_val = budget.get("total_budget")
    if not isinstance(total_budget_val, (int, float)):
        total_budget_val = 0.0

    estimated_cost_val = budget.get("estimated_cost")
    if not isinstance(estimated_cost_val, (int, float)):
        estimated_cost_val = 0.0

    remaining_val = budget.get("remaining")
    if not isinstance(remaining_val, (int, float)):
        remaining_val = total_budget_val - estimated_cost_val

    hotel_names = [h.get("name", "Unknown Hotel") for h in hotels if isinstance(h, dict)]

    return {
        "trip_id": trip_id,
        "source": trip.get("source", "N/A"),
        "destination": trip.get("destination", "N/A"),
        "duration_days": int(trip.get("days", 1)),
        "travel_mode": trip.get("travel_mode", "car"),
        "total_distance_km": round(float(total_dist), 2),
        "traveler_count": len(travelers) if isinstance(travelers, list) else 1,
        "total_budget": round(float(total_budget_val), 2),
        "estimated_cost": round(float(estimated_cost_val), 2),
        "remaining_budget": round(float(remaining_val), 2),
        "budget_status": budget.get("status", "N/A"),
        "hotel_count": len(hotels) if isinstance(hotels, list) else 0,
        "hotels": hotel_names[:5],
        "attractions_count": len(places) if isinstance(places, list) else 0,
        "weather_days_available": len(weather) if isinstance(weather, list) else 0,
        "weather_summary": [
            {
                "date": str(w.get("date", "N/A")),
                "min_temp": w.get("min_temp", "N/A"),
                "max_temp": w.get("max_temp", "N/A"),
            }
            for w in (weather[:int(trip.get("days", len(weather)))] if isinstance(weather, list) else [])
        ],
    }


def build_comparison(m1: dict, m2: dict) -> dict:
    c1, c2 = m1["estimated_cost"], m2["estimated_cost"]
    if c1 < c2:
        cheaper = m1["trip_id"]
    elif c2 < c1:
        cheaper = m2["trip_id"]
    else:
        cheaper = "equal"

    d1, d2 = m1["duration_days"], m2["duration_days"]
    if d1 < d2:
        shorter_duration = m1["trip_id"]
        longer_duration = m2["trip_id"]
    elif d2 < d1:
        shorter_duration = m2["trip_id"]
        longer_duration = m1["trip_id"]
    else:
        shorter_duration = "equal"
        longer_duration = "equal"

    dist1, dist2 = m1["total_distance_km"], m2["total_distance_km"]
    if dist1 < dist2:
        shorter_distance = m1["trip_id"]
        longer_distance = m2["trip_id"]
    elif dist2 < dist1:
        shorter_distance = m2["trip_id"]
        longer_distance = m1["trip_id"]
    else:
        shorter_distance = "equal"
        longer_distance = "equal"

    b1, b2 = m1["total_budget"], m2["total_budget"]
    if b1 > b2:
        higher_budget = m1["trip_id"]
    elif b2 > b1:
        higher_budget = m2["trip_id"]
    else:
        higher_budget = "equal"

    a1, a2 = m1["attractions_count"], m2["attractions_count"]
    if a1 > a2:
        more_attractions = m1["trip_id"]
    elif a2 > a1:
        more_attractions = m2["trip_id"]
    else:
        more_attractions = "equal"

    return {
        "cheaper_trip_id": cheaper,
        "cost_difference": round(abs(c1 - c2), 2),
        "shorter_duration_trip_id": shorter_duration,
        "longer_duration_trip_id": longer_duration,
        "duration_difference_days": abs(d1 - d2),
        "shorter_distance_trip_id": shorter_distance,
        "longer_distance_trip_id": longer_distance,
        "distance_difference_km": round(abs(dist1 - dist2), 2),
        "higher_budget_trip_id": higher_budget,
        "budget_difference": round(abs(b1 - b2), 2),
        "more_attractions_trip_id": more_attractions,
        "attractions_difference": abs(a1 - a2),
    }


@router.get("/compare")
def compare_trips(trip1: str, trip2: str):
    if not trip1 or not trip2:
        raise HTTPException(
            status_code=400,
            detail="Both 'trip1' and 'trip2' query parameters are required"
        )

    t1_data = load_trip(trip1)
    if t1_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trip '{trip1}' not found"
        )

    t2_data = load_trip(trip2)
    if t2_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trip '{trip2}' not found"
        )

    m1 = extract_comparison_metrics(t1_data, trip1)
    m2 = extract_comparison_metrics(t2_data, trip2)
    comparison = build_comparison(m1, m2)

    return {
        "trip1": m1,
        "trip2": m2,
        "comparison": comparison,
    }



@router.get("/{trip_id}/export")
def export_trip(trip_id: str):
    trip_data = load_trip(trip_id)

    if trip_data is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    trip_info = trip_data.get("trip", {})
    source = trip_info.get("source", "trip").split(",")[0].strip()
    destination = trip_info.get("destination", "destination").split(",")[0].strip()

    safe_source = re.sub(r'[<>:"/\\|?* ]', '_', source)
    safe_destination = re.sub(r'[<>:"/\\|?* ]', '_', destination)
    filename = f"{safe_source}_to_{safe_destination}_{trip_id[:8]}_export.json"

    export_payload = {
        "version": "1.0",
        "trip_id": trip_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "trip": trip_info,
        "dashboard": trip_data.get("dashboard", {}),
        "summary": trip_data.get("summary", {}),
        "notes": get_notes(trip_id),
        "rating": get_rating(trip_id),
        "is_favorite": is_favorite(trip_id),
        "expenses": get_expenses(trip_id),
    }

    content = json.dumps(export_payload, indent=2)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def compute_trip_insights(trip_wrapper: dict, trip_id: str) -> dict:
    trip = trip_wrapper.get("trip", {})
    route = trip.get("route", {})
    budget = trip.get("budget", {})
    travelers = trip.get("travelers", [])
    hotels = trip.get("hotels", [])
    day_schedule = trip.get("day_schedule", {})

    source = trip.get("source", "Origin")
    destination = trip.get("destination", "Destination")
    days = int(trip.get("days") or len(day_schedule) or 1)
    if days < 1:
        days = 1

    total_cost = float(budget.get("estimated_cost") or budget.get("total_budget") or 0.0)
    total_budget = float(budget.get("total_budget") or 0.0)
    traveler_count = max(len(travelers), 1)

    cost_per_traveler = round(total_cost / traveler_count, 2)
    cost_per_day = round(total_cost / days, 2)
    distance = float(route.get("distance_km") or 0.0)

    # Day-by-day calculations
    day_breakdown = []
    total_attractions = 0
    inter_stop_distances = []
    day_travel_distances = {}
    day_attraction_counts = {}

    for d_key, items in sorted(day_schedule.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
        if not isinstance(items, list):
            continue
        attr_count = len(items)
        total_attractions += attr_count
        day_attraction_counts[d_key] = attr_count

        d_dist = 0.0
        for i, item in enumerate(items):
            dist_prev = item.get("travel_from_previous_km")
            if isinstance(dist_prev, (int, float)):
                d_dist += float(dist_prev)
                if i > 0:
                    inter_stop_distances.append(float(dist_prev))

        day_travel_distances[d_key] = round(d_dist, 2)
        day_breakdown.append({
            "day": d_key,
            "attractions_count": attr_count,
            "travel_distance_km": round(d_dist, 2),
        })

    attractions_per_day = round(total_attractions / days, 2) if days > 0 else 0.0
    avg_stop_dist = (
        round(sum(inter_stop_distances) / len(inter_stop_distances), 2)
        if inter_stop_distances
        else 0.0
    )

    budget_util_pct = (
        round((total_cost / total_budget) * 100, 1) if total_budget > 0 else 0.0
    )
    hotel_count = len(hotels)

    metrics = {
        "total_trip_cost": total_cost,
        "cost_per_traveler": cost_per_traveler,
        "cost_per_day": cost_per_day,
        "distance": distance,
        "attractions_per_day": attractions_per_day,
        "average_distance_between_stops": avg_stop_dist,
        "traveler_count": traveler_count,
        "budget_utilization_pct": budget_util_pct,
        "hotel_count": hotel_count,
        "total_attractions": total_attractions,
        "days": days,
        "planned_budget": total_budget,
    }

    # Deterministic observations based on actual data
    observations = []

    # 1. Budget observation
    if total_budget > 0:
        if budget_util_pct > 100:
            over_amount = round(total_cost - total_budget, 2)
            observations.append({
                "category": "budget",
                "type": "warning",
                "title": "Budget Utilization Alert",
                "description": f"Budget utilization is high ({budget_util_pct}%). Estimated cost exceeds planned budget by ₹{over_amount:,.2f}."
            })
        elif budget_util_pct >= 85:
            remaining = round(total_budget - total_cost, 2)
            observations.append({
                "category": "budget",
                "type": "success",
                "title": "Optimal Budget Utilization",
                "description": f"Budget is well utilized ({budget_util_pct}%). You have a comfortable buffer of ₹{remaining:,.2f} remaining."
            })
        else:
            remaining = round(total_budget - total_cost, 2)
            observations.append({
                "category": "budget",
                "type": "info",
                "title": "Under Budget",
                "description": f"Trip is under budget ({budget_util_pct}% utilized) with ₹{remaining:,.2f} unallocated buffer."
            })
    else:
        observations.append({
            "category": "budget",
            "type": "info",
            "title": "Estimated Cost",
            "description": f"Total estimated trip cost is ₹{total_cost:,.2f} across {days} days."
        })

    # 2. Sightseeing intensity observation
    if day_attraction_counts:
        max_day = max(day_attraction_counts, key=day_attraction_counts.get)
        min_day = min(day_attraction_counts, key=day_attraction_counts.get)
        max_count = day_attraction_counts[max_day]
        min_count = day_attraction_counts[min_day]
        if max_count > min_count:
            observations.append({
                "category": "sightseeing",
                "type": "info",
                "title": "Sightseeing Intensity",
                "description": f"Day {max_day} has the highest number of attractions ({max_count}), while Day {min_day} has a lighter pace with {min_count} attractions."
            })
        else:
            observations.append({
                "category": "sightseeing",
                "type": "info",
                "title": "Sightseeing Balance",
                "description": f"Sightseeing is evenly paced with {max_count} attractions scheduled per day across all {days} days."
            })

    # 3. Travel & pacing observation
    if day_travel_distances:
        max_travel_day = max(day_travel_distances, key=day_travel_distances.get)
        max_travel_km = day_travel_distances[max_travel_day]
        avg_day_travel = round(sum(day_travel_distances.values()) / len(day_travel_distances), 2)
        if max_travel_km > (avg_day_travel * 1.3) and max_travel_km > 0:
            observations.append({
                "category": "travel",
                "type": "info",
                "title": "Travel Pacing Variation",
                "description": f"Day {max_travel_day} has significantly more local travel ({max_travel_km} km) than other days (daily average is {avg_day_travel} km)."
            })
        elif max_travel_km > 0:
            observations.append({
                "category": "travel",
                "type": "info",
                "title": "Even Transit Distribution",
                "description": f"Local travel between stops is well balanced across days, averaging {avg_day_travel} km per day."
            })

    if distance > 0:
        clean_source = source.split(",")[0].strip()
        clean_dest = destination.split(",")[0].strip()
        observations.append({
            "category": "route",
            "type": "info",
            "title": "Inter-City Distance",
            "description": f"Direct itinerary route spans {distance} km from {clean_source} to {clean_dest}."
        })

    # 4. Lodging & traveler distribution observation
    traveler_label = "traveler" if traveler_count == 1 else "travelers"
    hotel_label = "hotel option" if hotel_count == 1 else "hotel options"
    observations.append({
        "category": "group",
        "type": "info",
        "title": "Group & Lodging Logistics",
        "description": f"Configured for {traveler_count} {traveler_label} with an average cost of ₹{cost_per_traveler:,.2f} per person and {hotel_count} {hotel_label} identified."
    })

    return {
        "trip_id": trip_id,
        "metrics": metrics,
        "day_by_day_breakdown": day_breakdown,
        "observations": observations,
    }


@router.get("/{trip_id}/insights")
def get_trip_insights(trip_id: str):
    trip_data = load_trip(trip_id)

    if trip_data is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return compute_trip_insights(trip_data, trip_id)


@router.post("/import")
def import_trip(payload: dict = Body(...)):
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid request: expected a JSON object",
        )

    # 1. Resolve trip object (handles Step 36 export format, raw trip object, or wrapper format)
    if "trip" in payload and isinstance(payload["trip"], dict):
        trip_obj = payload["trip"]
    elif "source" in payload and "destination" in payload:
        trip_obj = payload
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid trip structure: missing core trip data",
        )

    # 2. Validate mandatory fields
    source = trip_obj.get("source")
    if not isinstance(source, str) or not source.strip():
        raise HTTPException(
            status_code=400,
            detail="Invalid trip data: 'source' must be a non-empty string",
        )

    destination = trip_obj.get("destination")
    if not isinstance(destination, str) or not destination.strip():
        raise HTTPException(
            status_code=400,
            detail="Invalid trip data: 'destination' must be a non-empty string",
        )

    days = trip_obj.get("days")
    if not isinstance(days, (int, float)) or int(days) < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid trip data: 'days' must be a positive integer",
        )
    days = int(days)

    day_schedule = trip_obj.get("day_schedule", {})
    if not isinstance(day_schedule, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid trip data: 'day_schedule' must be a dictionary",
        )

    travelers = trip_obj.get("travelers", [])
    if not isinstance(travelers, list):
        raise HTTPException(
            status_code=400,
            detail="Invalid trip data: 'travelers' must be a list",
        )

    # 3. Clean and sanitize core trip dictionary
    clean_trip = dict(trip_obj)
    clean_trip["source"] = source.strip()
    clean_trip["destination"] = destination.strip()
    clean_trip["days"] = days
    clean_trip["travelers"] = travelers
    clean_trip["day_schedule"] = day_schedule

    # Ensure route is well-formed
    route = trip_obj.get("route")
    if not isinstance(route, dict):
        route = {"distance_km": 0}
    clean_trip["route"] = route

    # Ensure budget is well-formed
    budget = trip_obj.get("budget")
    if not isinstance(budget, dict):
        budget = {
            "total_budget": 0,
            "estimated_cost": 0,
            "remaining": 0,
            "status": "Unknown",
            "categories": {},
        }
    clean_trip["budget"] = budget

    # Ensure lists are lists
    clean_trip["hotels"] = trip_obj.get("hotels", []) if isinstance(trip_obj.get("hotels"), list) else []
    clean_trip["places"] = trip_obj.get("places", []) if isinstance(trip_obj.get("places"), list) else []
    clean_trip["weather"] = trip_obj.get("weather", []) if isinstance(trip_obj.get("weather"), list) else []

    # Ensure destination_location exists so TripHistory can safely render
    dest_loc = trip_obj.get("destination_location")
    if not isinstance(dest_loc, dict) or "lat" not in dest_loc:
        clean_trip["destination_location"] = {"lat": 0.0, "lon": 0.0}

    # 4. Construct dashboard and summary
    dashboard = (
        payload.get("dashboard")
        if isinstance(payload.get("dashboard"), dict)
        else clean_trip.get("dashboard", {})
    )
    if not dashboard or not isinstance(dashboard, dict):
        dashboard = {
            "source": clean_trip["source"],
            "destination": clean_trip["destination"],
            "days": clean_trip["days"],
            "travel_mode": clean_trip.get("travel_mode", "car"),
            "weather": clean_trip.get("weather", []),
            "hotel_count": len(clean_trip.get("hotels", [])),
            "attraction_count": len(clean_trip.get("places", [])),
            "mandatory_count": len(clean_trip.get("mandatory_visits", [])),
            "distance": clean_trip.get("route", {}).get("distance_km", 0),
            "duration": clean_trip.get("days", 1),
            "budget": clean_trip.get("budget", {}),
        }

    summary = (
        payload.get("summary")
        if isinstance(payload.get("summary"), dict)
        else clean_trip.get("summary", {})
    )
    if not summary or not isinstance(summary, dict):
        summary = {
            "days": clean_trip["days"],
            "distance": clean_trip.get("route", {}).get("distance_km", 0),
            "travel_time": clean_trip.get("route", {}).get("duration_hr", "N/A"),
            "hotel_count": len(clean_trip.get("hotels", [])),
            "place_count": len(clean_trip.get("places", [])),
            "scheduled_activities": sum(len(p) for p in clean_trip.get("day_schedule", {}).values()),
            "travelers": len(clean_trip.get("travelers", [])),
            "travel_mode": clean_trip.get("travel_mode", "car"),
        }

    # 5. Save with a new trip ID to ensure no existing trip is accidentally overwritten
    new_trip_payload = {
        "trip": clean_trip,
        "dashboard": dashboard,
        "summary": summary,
    }
    new_trip_id = save_trip(new_trip_payload)

    # 6. Restore auxiliary metadata when present
    # Notes
    imported_notes = payload.get("notes") or clean_trip.get("notes")
    if isinstance(imported_notes, list):
        for note in imported_notes:
            if isinstance(note, str) and note.strip():
                add_note(new_trip_id, note.strip())

    # Rating
    imported_rating = payload.get("rating") or clean_trip.get("rating")
    if isinstance(imported_rating, dict) and "rating" in imported_rating:
        r_val = imported_rating.get("rating")
        if isinstance(r_val, int) and 1 <= r_val <= 5:
            save_rating(new_trip_id, r_val, str(imported_rating.get("feedback", "")))

    # Favorite state
    if payload.get("is_favorite") is True:
        add_favorite(new_trip_id)

    # Expenses
    imported_expenses = payload.get("expenses") or clean_trip.get("expenses")
    if isinstance(imported_expenses, list):
        for exp in imported_expenses:
            if isinstance(exp, dict):
                add_expense(new_trip_id, exp)

    return {
        "trip_id": new_trip_id,
        "message": "Trip imported successfully",
        "source": clean_trip["source"],
        "destination": clean_trip["destination"],
    }


@router.get("/{trip_id}")
def get_trip(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return trip


@router.post("/{trip_id}/duplicate")
def duplicate_trip(trip_id: str):
    original_trip_data = load_trip(trip_id)

    if original_trip_data is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    # Deep copy the trip data so changes to the duplicate do not mutate the original
    new_trip_data = copy.deepcopy(original_trip_data)

    # Save as a new trip with a unique trip ID
    new_trip_id = save_trip(new_trip_data)

    # Metadata decisions:
    # 1. Notes: Copy existing notes over to the duplicate under new_trip_id
    #    so the user keeps their itinerary reminders, but can edit them independently.
    existing_notes = get_notes(trip_id)
    if isinstance(existing_notes, list):
        for note in existing_notes:
            if isinstance(note, str) and note.strip():
                add_note(new_trip_id, note.strip())

    # 2. Rating: Reset (do not copy rating to the new clone, it has not yet been experienced)
    # 3. Favorite state: Reset (do not favorite the new clone by default)
    # 4. Expenses: Reset (no expenses logged yet on the new clone)

    return {
        "trip_id": new_trip_id,
        "original_trip_id": trip_id,
        "message": "Trip duplicated successfully"
    }


@router.post("/{trip_id}/favorite")
def favorite_trip(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    add_favorite(trip_id)

    return {
        "trip_id": trip_id,
        "favorite": True
    }


@router.delete("/{trip_id}/favorite")
def unfavorite_trip(trip_id: str):
    remove_favorite(trip_id)

    return {
        "trip_id": trip_id,
        "favorite": False
    }


@router.get("/{trip_id}/favorite")
def check_favorite(trip_id: str):
    return {
        "trip_id": trip_id,
        "favorite": is_favorite(trip_id)
    }
@router.get("/{trip_id}/notes")
def get_trip_notes(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return {
        "trip_id": trip_id,
        "notes": get_notes(trip_id)
    }


@router.post("/{trip_id}/notes")
def create_trip_note(
    trip_id: str,
    note: str
):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    if not note.strip():
        raise HTTPException(
            status_code=400,
            detail="Note cannot be empty"
        )

    notes = add_note(
        trip_id,
        note.strip()
    )

    return {
        "trip_id": trip_id,
        "notes": notes
    }


@router.delete("/{trip_id}/notes/{note_index}")
def remove_trip_note(
    trip_id: str,
    note_index: int
):
    deleted = delete_note(
        trip_id,
        note_index
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    return {
        "trip_id": trip_id,
        "deleted": True
    }
@router.get("/{trip_id}/rating")
def get_trip_rating(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return {
        "trip_id": trip_id,
        "rating": get_rating(trip_id)
    }


@router.post("/{trip_id}/rating")
def rate_trip(
    trip_id: str,
    rating: int,
    feedback: str = ""
):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    if rating < 1 or rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5"
        )

    result = save_rating(
        trip_id,
        rating,
        feedback.strip()
    )

    return {
        "trip_id": trip_id,
        **result
    }


@router.post("/{trip_id}/template")
def convert_trip_to_template(
    trip_id: str,
    payload: dict = Body(default_factory=dict)
):
    from backend.services.storage.template_store import save_template_from_trip
    name = payload.get("name", "")
    description = payload.get("description", "")
    category = payload.get("category", "General")

    try:
        template = save_template_from_trip(
            trip_id=trip_id,
            name=name,
            description=description,
            category=category,
        )
        return {
            "message": "Template created successfully from trip",
            "template_id": template["id"],
            "name": template["name"],
            "destination": template["destination"],
            "duration_days": template["duration_days"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")

