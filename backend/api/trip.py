from fastapi import APIRouter
from services.storage.trip_store import get_trip

router = APIRouter()

@router.get("/trip/{trip_id}")
def fetch_trip(trip_id: str):
    trip = get_trip(trip_id)

    if not trip:
        return {"error": "Trip not found"}

    return trip