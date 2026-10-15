from typing import Optional
from fastapi import APIRouter, Header, Query
from backend.models.trip import TripRequest, SuggestDatesRequest
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


@router.post("/suggest-dates")
async def suggest_dates_endpoint(
    request: SuggestDatesRequest,
):
    try:
        from backend.services.planner.date_suggester import suggest_travel_dates
        suggestions = await suggest_travel_dates(
            destination=request.destination,
            days=request.days,
            source=request.source,
            flexible_window=request.flexible_window,
            earliest_date=request.earliest_date,
            latest_date=request.latest_date,
            travelers_count=request.travelers_count or 1,
            budget=request.budget,
            interests=request.interests,
            weather_preference=request.weather_preference,
            prefer_weekends=request.prefer_weekends,
        )
        return {"success": True, "data": suggestions}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to suggest travel dates: {str(e)}")