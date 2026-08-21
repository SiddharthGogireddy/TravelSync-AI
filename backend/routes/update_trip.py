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
from backend.services.external.place_service import find_place

from backend.services.planner.budget_tracker import (
    calculate_budget,
)
from backend.services.planner.budget_replanner import (
    fit_trip_to_budget,
)
import re
from backend.services.planner.day_regenerator import (
    regenerate_day,
)


router = APIRouter(
    prefix="/trip",
    tags=["Trip Update"],
)
def normalize_place_name(name):
    return re.sub(
        r"[^a-z0-9]",
        "",
        name.lower(),
    )

@router.patch("/{trip_id}")
async def update_trip(
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
        if "add_place" in parsed:

            place_name = parsed["add_place"]

            destination = trip["trip"]["destination_location"]

            place = await find_place(
                place_name,
                destination["lat"],
                destination["lon"],
            )

            if place is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Place '{place_name}' not found",
                )   

            new_place = {
                "name": place.get("name", place_name),
                "category": (
                    place.get("kinds", "")
                    .split(",")[0]
                    .replace("_", " ")
                    .title()
                ),
                "distance_km": round(
                    place.get("dist", 0) / 1000,
                    2,
                ),
                "lat": place.get(
                    "point", {}
                ).get("lat"),
                "lon": place.get(
                    "point", {}
                ).get("lon"),
                "score": 0,
                "matched_travelers": [],
                "match_count": 0,
            }

            trip["trip"]["places"].append(
                new_place
            )
            day_schedule = trip["trip"].get(
                "day_schedule",
                {}
            )

            if day_schedule:

                target_day = min(
                day_schedule,
                key=lambda day: len(
                day_schedule[day]
                )
            )

                day_schedule[target_day].append(
                    new_place
                )

                trip["trip"]["day_schedule"] = (
                    day_schedule
                )
        if "remove_place" in parsed:

            place_name = normalize_place_name(
                parsed["remove_place"]                
            )

            # Remove from available places
            trip["trip"]["places"] = [
                place
                for place in trip["trip"]["places"]
                if normalize_place_name(place["name"])!= place_name
            ]

                # Remove from daily schedule
            day_schedule = trip["trip"].get(
                "day_schedule",
                {}
            )

            for day, places in day_schedule.items():

                day_schedule[day] = [
                    place
                    for place in places
                    if normalize_place_name(place["name"])
                    != place_name
                ]

            trip["trip"]["day_schedule"] = (
                day_schedule
            )
            scheduled_activity_count = sum(
                len(day_places)
                for day_places in day_schedule.values() 
            )

            trip["trip"]["budget"] = calculate_budget(
                trip["trip"]["travelers"],
                trip["trip"]["days"],
                trip["trip"]["travel_mode"],
                trip["trip"]["hotels"],
                trip["trip"]["places"],
                scheduled_activity_count=scheduled_activity_count,
                total_budget=trip["trip"]["budget"]["total_budget"],
            )
        if "budget" in parsed:

            trip = fit_trip_to_budget(
                trip,
                parsed["budget"],
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
    if "regenerate_day" in parsed:

        trip = regenerate_day(
            trip,
            parsed["regenerate_day"],
        )
    update_saved_trip(
        trip_id,
        trip,
    )

    return trip