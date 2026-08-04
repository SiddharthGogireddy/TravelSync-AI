from typing import List,Literal

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
class MandatoryVisit(BaseModel):
    name: str
    day: int | None = None
class TripRequest(BaseModel):
    source: str
    destination: str
    days: int
    travelers: List[Traveler]
    mandatory_visits: List[MandatoryVisit] = []

class TripRequest(BaseModel):
    source: str
    destination: str
    days: int
    travelers: list[Traveler]
    mandatory_visits: list[MandatoryVisit] = []
    travel_mode: Literal[
        "car",
        "bus",
        "train",
        "flight"
    ]




@router.post("/")
async def planner(request: TripRequest):
    result = await build_trip(
        request
    )

    return result