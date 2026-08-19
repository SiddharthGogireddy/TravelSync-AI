from fastapi import APIRouter, HTTPException

from backend.models.trip_update import (
    TripUpdateRequest,
)
from backend.services.trip_editor.prompt_parser import (
    parse_prompt,
)
from backend.services.storage.trip_store import (
    load_trip,update_saved_trip
)
from backend.services.planner.budget_tracker import (
    calculate_budget,
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
    if update.prompt:

        parsed = parse_prompt(
            update.prompt
        )

        if "budget" in parsed:

            traveler_profiles = (
            trip["trip"]["travelers"]
            )

            days = trip["trip"]["days"]

            travel_mode = (
                trip["trip"]["travel_mode"]
            )

            hotels = (
                trip["trip"]["hotels"]
            )

            places = (
            trip["trip"]["places"]
            )

            new_budget = calculate_budget(
                traveler_profiles,
                days,
                travel_mode,
                hotels,
                places,
            )

            new_budget["total_budget"] = (
                parsed["budget"]
            )

            trip["trip"]["budget"] = (
                new_budget
            )

            update_saved_trip(
                trip_id,
                trip,
        )
        return trip
    if update.budget is not None:

        trip["trip"]["budget"]["total_budget"] = (
            update.budget
        )

    update_saved_trip(
        trip_id,
        trip,
    )

    return trip