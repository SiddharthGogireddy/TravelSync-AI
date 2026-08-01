from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from services.planner.trip_planner import build_trip

router = APIRouter(
    prefix="/planner",
    tags=["Trip Planner"]
)
class Traveler(BaseModel):
    name: str
    interests: List[str]
    budget: str
    pace: str
class TripRequest(BaseModel):
    source: str
    destination: str
    days: int
    travelers: List[Traveler]

@router.post("/")
async def planner(request: TripRequest):
    result = await build_trip(
        request
    )

    return result