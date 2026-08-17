from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import (
    FileResponse,
)

from backend.services.storage.trip_store import load_trip

router = APIRouter(
    prefix="/trip",
    tags=["Trip"]
)


@router.get("/{trip_id}")
def get_trip(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return trip

