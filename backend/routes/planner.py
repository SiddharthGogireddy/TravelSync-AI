from fastapi import APIRouter
from pydantic import BaseModel

from services.planner.trip_planner import build_trip

router = APIRouter(
    prefix="/planner",
    tags=["Trip Planner"]
)

class TripRequest(BaseModel):
    source: str
    destination: str


@router.post("/")
async def planner(request: TripRequest):
    result = await build_trip(
        request.source,
        request.destination
    )

    return result