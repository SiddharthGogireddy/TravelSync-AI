from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

from backend.routes import trip
from backend.services.storage.trip_store import load_trip
from backend.services.trip_editor.explanation_service import explain_attraction
from backend.services.auth.authorization import extract_user_id, verify_trip_access
from backend.utils.helpers import normalize_place_name

router = APIRouter()


class ExplanationRequest(BaseModel):
    place_name: str


@router.post("/{trip_id}")
def explain_place(
    trip_id: str,
    request: ExplanationRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    trip = trip_record.get("data")
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip_data = trip.get("trip", trip) if isinstance(trip, dict) else {}

    place = None

# First search the actual scheduled attractions
    for day_places in trip_data.get("day_schedule", {}).values():
        for candidate in day_places:
            if normalize_place_name(candidate.get("name", "")) == normalize_place_name(  request.place_name):
                place = candidate
                break

        if place:
            break

    # Fallback to the general place list
    if not place:
        place = next(
            (
                candidate
                for candidate in trip_data.get("places", [])
                if normalize_place_name(candidate.get("name", "")) == normalize_place_name(request.place_name)
            ),
            None,
        )

    if not place:
        raise HTTPException(
            status_code=404,
            detail="Attraction not found in this trip",
        )

    explanation = explain_attraction(place, trip_data)

    return {
        "place": place["name"],
        "explanation": explanation,
    }