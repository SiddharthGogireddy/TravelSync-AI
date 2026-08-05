from services.planner.distance import haversine


def optimize_trip(
    places,
    days,
    mandatory_schedule=None
):
    """
    Creates a balanced itinerary by:
    - Respecting mandatory visits
    - Prioritizing higher scored attractions
    - Grouping nearby attractions
    - Limiting attractions per day
    """

    MAX_PER_DAY = 4
    MAX_CLUSTER_DISTANCE = 5  # km

    if mandatory_schedule is None:
        mandatory_schedule = {}

    # Sort by score (highest first)
    places = sorted(
        places,
        key=lambda x: (
            -x["score"],
            x["distance_km"]
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
    # Fill nearby attractions around mandatory ones
    # -------------------------------------------------

    for day in schedule:

        if len(schedule[day]) == 0:
            continue

        base_place = schedule[day][0]

        if (
            base_place.get("lat") is None
            or base_place.get("lon") is None
        ):
            continue

        for place in places:

            if place["name"] in used:
                continue

            if (
                place.get("lat") is None
                or place.get("lon") is None
            ):
                continue

            if len(schedule[day]) >= MAX_PER_DAY:
                break

            distance = haversine(
                base_place["lat"],
                base_place["lon"],
                place["lat"],
                place["lon"]
            )

            if distance <= MAX_CLUSTER_DISTANCE:

                schedule[day].append(place)
                used.add(place["name"])

    # -------------------------------------------------
    # STEP 3
    # Fill remaining days
    # -------------------------------------------------

    for place in places:

        if place["name"] in used:
            continue

        for day in schedule:

            if len(schedule[day]) >= MAX_PER_DAY:
                continue

            if len(schedule[day]) == 0:

                schedule[day].append(place)
                used.add(place["name"])
                break

            base_place = schedule[day][0]

            if (
                base_place.get("lat") is None
                or base_place.get("lon") is None
                or place.get("lat") is None
                or place.get("lon") is None
            ):
                continue

            distance = haversine(
                base_place["lat"],
                base_place["lon"],
                place["lat"],
                place["lon"]
            )

            if distance <= MAX_CLUSTER_DISTANCE:

                schedule[day].append(place)
                used.add(place["name"])
                break

    # -------------------------------------------------
    # STEP 4
    # Put any remaining attractions wherever space exists
    # -------------------------------------------------

    for place in places:

        if place["name"] in used:
            continue

        for day in schedule:

            if len(schedule[day]) < MAX_PER_DAY:

                schedule[day].append(place)
                used.add(place["name"])
                break

    return schedule