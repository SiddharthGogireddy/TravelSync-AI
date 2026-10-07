import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from backend.services.expense.expense_store import get_expenses
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
