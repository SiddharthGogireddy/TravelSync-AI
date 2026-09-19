from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.storage.trip_store import load_trip
from backend.services.trip_editor.explanation_service import explain_attraction


router = APIRouter()


class ExplanationRequest(BaseModel):
    place_name: str


@router.post("/{trip_id}")
def explain_place(trip_id: str, request: ExplanationRequest):

    trip = load_trip(trip_id)

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    place = next(
        (
            place
            for place in trip.get("places", [])
            if place.get("name", "").lower() == request.place_name.lower()
        ),
        None,
    )

    if not place:
        raise HTTPException(
            status_code=404,
            detail="Attraction not found in this trip",
        )

    explanation = explain_attraction(place, trip)

    return {
        "place": place["name"],
        "explanation": explanation,
    }