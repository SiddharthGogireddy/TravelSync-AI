
from backend.services.planner.distance import haversine


def optimize_trip(
    places,
    days,
    mandatory_schedule=None,
    pace="Balanced",
):
    """
    Creates a balanced itinerary by:
    - Respecting mandatory visits
    - Prioritizing higher scored attractions
    - Grouping nearby attractions
    - Limiting attractions per day
    """

    PACE_LIMITS = {
        "Relaxed": 3,
        "Balanced": 4,
        "Fast": 5,
    }

    pace_limit = PACE_LIMITS.get(
        pace,
        4,
    )

    average_places_per_day = (
        len(places) + days - 1
    ) // days

    MAX_PER_DAY = max(
        1,
        min(
            pace_limit,
            average_places_per_day,
        )
    )
    MAX_CLUSTER_DISTANCE = 5  # km

    if mandatory_schedule is None:
        mandatory_schedule = {}

    # Sort by score (highest first)
    places = sorted(
        places,
        key=lambda x: (
            -x["score"],
            -x.get("match_count", 0),
            x["distance_km"],
        )
    )

    # Empty schedule
    schedule = {
        str(day): []
        for day in range(1, days + 1)
    }

    used = set()

    # -------------------------------------------------
    # STEP 1
    # Add mandatory visits first
    # -------------------------------------------------

    for day, mandatory_places in mandatory_schedule.items():

        for mandatory in mandatory_places:

            for place in places:

                if place["name"] == mandatory:

                    schedule[day].append(place)
                    used.add(place["name"])
                    break

    
    # -------------------------------------------------
# STEP 2
# Build geographically efficient and diverse
# day clusters
# -------------------------------------------------

    for day in schedule:

        if len(schedule[day]) == 0:
            continue

        covered_interests = set()

        for existing_place in schedule[day]:
            covered_interests.update(
                existing_place.get(
                    "matched_interests",
                    []
                )
            )

        while len(schedule[day]) < MAX_PER_DAY:

            current_place = schedule[day][-1]

            if (
                current_place.get("lat") is None
                or current_place.get("lon") is None
            ):
                break

            best_place = None
            best_value = None

            for place in places:

                if place["name"] in used:
                    continue

                if (
                    place.get("lat") is None
                    or place.get("lon") is None
                ):
                    continue

                distance = haversine(
                    current_place["lat"],
                    current_place["lon"],
                    place["lat"],
                    place["lon"],
                )

                if distance > MAX_CLUSTER_DISTANCE:
                    continue

                place_interests = set(
                    place.get(
                        "matched_interests",
                        []
                    )
                )

                new_interests = (
                    place_interests - covered_interests
                )

                diversity_bonus = (
                    len(new_interests) * 3
                )

                value = (
                    place.get("score", 0)
                    + diversity_bonus
                    - distance * 0.5
                )

                if (
                    best_value is None
                    or value > best_value
                ):
                    best_value = value
                    best_place = place

            if best_place is None:
                break

            schedule[day].append(
                best_place
            )

            used.add(
                best_place["name"]
            )

            covered_interests.update(
                best_place.get(
                    "matched_interests",
                    []
                )
            )
    # -------------------------------------------------
    # STEP 3
    # Fill remaining days
    # -------------------------------------------------
    remaining = [
    place
    for place in places
    if place["name"] not in used
    ]

    day_keys = list(schedule.keys())

    day_index = 0
    for place in remaining:

        available_days = [
            day
            for day in day_keys
            if len(schedule[day]) < MAX_PER_DAY
        ]

        if not available_days:
            break

        best_day = None
        best_distance = None

        if (
            place.get("lat") is not None
            and place.get("lon") is not None
        ):

            for day in available_days:

                if not schedule[day]:
                    distance = 0

                else:
                    last_place = schedule[day][-1]

                    if (
                        last_place.get("lat") is None
                        or last_place.get("lon") is None
                    ):
                        continue

                    distance = haversine(
                        last_place["lat"],
                        last_place["lon"],
                        place["lat"],
                        place["lon"],
                    )

                if (
                    best_distance is None
                    or distance < best_distance
                ):
                    best_distance = distance
                    best_day = day

        # Fallback if coordinates are unavailable
        if best_day is None:
            best_day = min(
                available_days,
                key=lambda d: len(schedule[d])
            )

        schedule[best_day].append(place)
        used.add(place["name"])
    scheduled = sum(
        len(day)
        for day in schedule.values()
)
    print("Scheduled:", scheduled)
    print("Available:", len(places))
    for day, day_places in schedule.items():

        for index, place in enumerate(day_places):

            if index == 0:
                place["travel_from_previous_km"] = 0
                continue

            previous = day_places[index - 1]

            if (
                previous.get("lat") is None
                or previous.get("lon") is None
                or place.get("lat") is None
                or place.get("lon") is None
            ):
                place["travel_from_previous_km"] = None
                continue

            distance = haversine(
                previous["lat"],
                previous["lon"],
                place["lat"],
                place["lon"],
            )

            place["travel_from_previous_km"] = round(
                distance,
                2,
            )
    print("\nFINAL DAY SCHEDULE:")

    for day, day_places in schedule.items():
        print(f"\nDAY {day}")

        for place in day_places:
            print(
                place["name"],
                "→",
                place.get("travel_from_previous_km"),
                "km"
            )
    return schedule