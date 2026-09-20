from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.routes import trip
from backend.services.storage.trip_store import load_trip
from backend.services.trip_editor.explanation_service import explain_attraction
from backend.utils.helpers import normalize_place_name

router = APIRouter()


class ExplanationRequest(BaseModel):
    place_name: str


@router.post("/{trip_id}")
def explain_place(trip_id: str, request: ExplanationRequest):

    trip = load_trip(trip_id)
    trip_data = trip["trip"]
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

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