from backend.services.planner.budget_tracker import (
    calculate_budget,
)


def regenerate_day(trip, day_number):

    trip_data = trip["trip"]

    day_schedule = trip_data.get(
        "day_schedule",
        {}
    )

    day_key = str(day_number)

    if day_key not in day_schedule:
        return trip

    current_day = day_schedule[day_key]

    current_names = {
        place["name"].strip().lower()
        for place in current_day
    }

    mandatory_visits = trip_data.get(
        "mandatory_visits",
        []
    )

    mandatory_names = {
        visit["name"].strip().lower()
        for visit in mandatory_visits
        if visit.get("name")
    }

    # Places used on other days
    used_elsewhere = set()

    for other_day, places in day_schedule.items():

        if other_day == day_key:
            continue

        for place in places:
            used_elsewhere.add(
                place["name"].strip().lower()
            )

    available_places = trip_data.get(
        "places",
        []
    )

    candidates = []

    for place in available_places:

        name = place["name"].strip().lower()

        # Don't select the same attractions
        if name in current_names:
            continue

        if name in used_elsewhere:
            continue

        # Don't replace protected mandatory visits
        if name in mandatory_names:
            continue

        candidates.append(place)

    # Highest quality matches first
    candidates.sort(
        key=lambda place: (
            place.get("score", 0),
            place.get("match_count", 0),
        ),
        reverse=True,
    )

    number_of_places = len(current_day)

    new_day = candidates[
        :number_of_places
    ]

    day_schedule[day_key] = new_day

    trip_data["day_schedule"] = (
        day_schedule
    )
    scheduled_activity_count = sum(
        len(day_places)
        for day_places in day_schedule.values()
    )
    
    trip_data["budget"] = calculate_budget(
        trip_data["travelers"],
        trip_data["days"],
        trip_data["travel_mode"],
        trip_data["hotels"],
        trip_data["places"],
        scheduled_activity_count=scheduled_activity_count,
        total_budget=trip_data["budget"]["total_budget"],
)

    return trip