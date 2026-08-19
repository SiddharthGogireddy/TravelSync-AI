from fastapi import APIRouter, HTTPException

from backend.models.trip_update import (
    TripUpdateRequest,
)

from backend.services.storage.trip_store import (
    load_trip,update_saved_trip
)

router = APIRouter(
    prefix="/trip",
    tags=["Trip Update"],
)


@router.patch("/{trip_id}")
def update_trip(
    trip_id: str,
    update: TripUpdateRequest,
):

    trip = load_trip(trip_id)

    if trip is None:

        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    if update.budget is not None:

        trip["trip"]["budget"]["total_budget"] = (
            update.budget
        )

    update_saved_trip(
        trip_id,
        trip,
    )

    return trip