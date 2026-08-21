from backend.services.planner.budget_tracker import (
    calculate_budget,
)


def fit_trip_to_budget(
    trip,
    target_budget,
):
    trip_data = trip["trip"]

    travelers = trip_data["travelers"]
    days = trip_data["days"]
    travel_mode = trip_data["travel_mode"]
    hotels = trip_data["hotels"]
    places = trip_data["places"]

    mandatory_visits = trip_data.get(
        "mandatory_visits",
        [],
    )

    mandatory_names = {
        visit["name"].strip().lower()
        for visit in mandatory_visits
        if visit.get("name")
    }

    day_schedule = trip_data.get(
        "day_schedule",
        {},
    )

    while True:

        scheduled_count = sum(
            len(day_places)
            for day_places in day_schedule.values()
        )

        budget = calculate_budget(
            travelers,
            days,
            travel_mode,
            hotels,
            places,
            scheduled_activity_count=scheduled_count,
            total_budget=target_budget,
        )

        trip_data["budget"] = budget

        if budget["estimated_cost"] <= target_budget:
            break

        candidates = []

        for day, day_places in day_schedule.items():

            for index, place in enumerate(day_places):

                name = place["name"].strip().lower()

                if name in mandatory_names:
                    continue

                full_place = next(
                    (
                        p
                        for p in places
                        if p["name"].strip().lower()
                        == name
                    ),
                    place,
                )

                candidates.append(
                    {
                        "day": day,
                        "index": index,
                        "place": full_place,
                    }
                )

        if not candidates:
            break

        candidates.sort(
            key=lambda item: (
                item["place"].get("score", 0),
                item["place"].get(
                    "match_count",
                    0,
                ),
            )
        )

        remove = candidates[0]

        day_schedule[
            remove["day"]
        ].pop(remove["index"])

    trip_data["day_schedule"] = day_schedule

    return trip