from typing import Optional
from fastapi import APIRouter, Header, Query
from backend.models.trip import TripRequest
from backend.services.auth.authorization import extract_user_id
from backend.services.gemini_service import generate
from backend.services.planner.itinerary import build_trip

router = APIRouter(
    prefix="/planner",
    tags=["Trip Planner"]
)


@router.post("/")
async def planner(
    request: TripRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id) or getattr(request, "user_id", None)
    result = await build_trip(request, owner_id=uid)
    if not isinstance(result, dict) or "trip" not in result:
        return result

    trip_info = result["trip"]
    destination_title = trip_info.get("destination", request.destination)
    trip_days = trip_info.get("days", request.days)

    place_names = [
        p["name"]
        for p in trip_info.get("places", [])[:10]
    ]

    hotel_names = [
        h["name"]
        for h in trip_info.get("hotels", [])[:5]
    ]

    prompt = f"""
Generate a {trip_days}-day travel itinerary.

Source: {request.source}

Destination: {destination_title}

Travel mode: {request.travel_mode}


Traveler interests:

{[t.interests for t in request.travelers]}

Recommended attractions:

{place_names}

Recommended hotels:

{hotel_names}

Return ONLY valid JSON.

Format:

{{
    "days": [
        {{
            "day": 1,
            "title": "",
            "activities": [],
            "food": [],
            "budget": ""
        }}
    ]
}}
"""

    try:
        itinerary = generate(prompt)

    except Exception as e:
        print("Gemini error:", e)

        itinerary = {
            "days": []
        }

    result["itinerary"] = itinerary

    trip_id = result.get("trip_id")
    if trip_id and itinerary:
        from backend.services.storage.trip_store import load_trip, update_saved_trip
        saved_record = load_trip(trip_id)
        if isinstance(saved_record, dict):
            saved_record["itinerary"] = itinerary
            if "trip" in saved_record and isinstance(saved_record["trip"], dict):
                saved_record["trip"]["itinerary"] = itinerary
            update_saved_trip(trip_id, saved_record)

    return result