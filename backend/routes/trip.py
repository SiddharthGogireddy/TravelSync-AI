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
