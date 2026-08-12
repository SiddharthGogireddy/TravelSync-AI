

from fastapi import APIRouter
from backend.models.trip import TripRequest

from backend.services.gemini_service import generate
from backend.services.planner.itinerary import build_trip

router = APIRouter(
    prefix="/planner",
    tags=["Trip Planner"]
)






@router.post("/")
async def planner(request: TripRequest):
    result = await build_trip(
        request
    )
    prompt = f"""
Generate a {request.days}-day travel itinerary.

Destination: {request.destination}

Travelers:
{len(request.travelers)}

Interests:
{[t.interests for t in request.travelers]}

Return ONLY valid JSON.

Format:

{{
  "days":[
    {{
      "day":1,
      "title":"string",
      "activities":["string"],
      "food":["string"],
      "budget":"string"
    }}
  ]
}}
"""

    itinerary = generate(prompt)

    result["itinerary"] = itinerary

    return result
    
    itinerary = generate(prompt)

    result["itinerary"] = itinerary

    return result