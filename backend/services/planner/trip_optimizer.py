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
    - Covering all requested group interests
    - Prioritizing higher scored attractions
    - Grouping nearby attractions
    - Limiting attractions per day
    """

    PACE_LIMITS = {
        "Relaxed": 3,
        "Balanced": 4,
        "Fast": 5,
    }

    pace_limit = PACE_LIMITS.get(pace, 4)

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

    MAX_CLUSTER_DISTANCE = 5

    if mandatory_schedule is None:
        mandatory_schedule = {}

    # -------------------------------------------------
    # Sort places by quality
    # -------------------------------------------------

    places = sorted(
        places,
        key=lambda x: (
            -x.get("score", 0),
            -x.get("match_count", 0),
            x.get("distance_km", 0),
        )
    )

    # -------------------------------------------------
    # Create empty schedule
    # -------------------------------------------------

    schedule = {
        str(day): []
        for day in range(1, days + 1)
    }

    used = set()

    # -------------------------------------------------
    # Find all interests requested by the group
    # -------------------------------------------------

    group_interests = set()

    for place in places:
        group_interests.update(
            place.get(
                "matched_interests",
                []
            )
        )

    print(
        "GROUP INTERESTS:",
        group_interests
    )

    covered_group_interests = set()

    # -------------------------------------------------
    # STEP 1
    # Add mandatory visits first
    # -------------------------------------------------

    for day, mandatory_places in mandatory_schedule.items():

        day = str(day)

        if day not in schedule:
            continue

        for mandatory in mandatory_places:

            for place in places:

                if place["name"] == mandatory:

                    if (
                        len(schedule[day])
                        < MAX_PER_DAY
                    ):
                        schedule[day].append(
                            place
                        )

                        used.add(
                            place["name"]
                        )

                    break

    # -------------------------------------------------
    # STEP 2
    # Build daily itinerary
    # -------------------------------------------------

    for day in schedule:

        covered_interests = set()

        # Include mandatory visits already placed
        for existing_place in schedule[day]:

            existing_interests = set(
                existing_place.get(
                    "matched_interests",
                    []
                )
            )

            covered_interests.update(
                existing_interests
            )

            covered_group_interests.update(
                existing_interests
            )

        # -------------------------------------------------
        # STEP 2A
        # Ensure all group interests are represented
        # -------------------------------------------------

        while (
            len(schedule[day]) < MAX_PER_DAY
            and covered_group_interests
            != group_interests
        ):

            missing_interests = (
                group_interests
                - covered_group_interests
            )

            print(
                "DAY",
                day,
                "MISSING INTERESTS:",
                missing_interests
            )

            best_place = None
            best_value = None

            for place in places:

                if place["name"] in used:
                    continue

                place_interests = set(
                    place.get(
                        "matched_interests",
                        []
                    )
                )

                new_interests = (
                    place_interests
                    & missing_interests
                )

                if not new_interests:
                    continue

                # Strongly prioritize places that
                # cover currently missing interests.
                value = (
                    len(new_interests) * 100
                    + place.get("score", 0)
                    - place.get(
                        "distance_km",
                        0
                    ) * 0.5
                )

                if (
                    best_value is None
                    or value > best_value
                ):
                    best_value = value
                    best_place = place

            if best_place is None:

                print(
                    "NO PLACE FOUND FOR:",
                    missing_interests
                )

                break

            print(
                "COVERAGE SELECTED:",
                best_place["name"],
                best_place.get(
                    "matched_interests",
                    []
                )
            )

            schedule[day].append(
                best_place
            )

            used.add(
                best_place["name"]
            )

            best_interests = set(
                best_place.get(
                    "matched_interests",
                    []
                )
            )

            covered_interests.update(
                best_interests
            )

            covered_group_interests.update(
                best_interests
            )

        # -------------------------------------------------
        # STEP 2B
        # Fill remaining slots using nearby attractions
        # -------------------------------------------------

        while len(schedule[day]) < MAX_PER_DAY:

            # If somehow the day is still empty,
            # choose the best remaining attraction.
            if not schedule[day]:

                best_place = None

                for place in places:

                    if place["name"] in used:
                        continue

                    if (
                        best_place is None
                        or place.get("score", 0)
                        > best_place.get("score", 0)
                    ):
                        best_place = place

                if best_place is None:
                    break

                schedule[day].append(
                    best_place
                )

                used.add(
                    best_place["name"]
                )

                best_interests = set(
                    best_place.get(
                        "matched_interests",
                        []
                    )
                )

                covered_interests.update(
                    best_interests
                )

                covered_group_interests.update(
                    best_interests
                )

                continue

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

                # Interests not yet represented
                # on this particular day.
                new_day_interests = (
                    place_interests
                    - covered_interests
                )

                day_diversity_bonus = (
                    len(new_day_interests) * 8
                )

                value = (
                    place.get("score", 0)
                    + day_diversity_bonus
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

            best_interests = set(
                best_place.get(
                    "matched_interests",
                    []
                )
            )

            covered_interests.update(
                best_interests
            )

            covered_group_interests.update(
                best_interests
            )

    # -------------------------------------------------
    # STEP 3
    # Fill any remaining available slots
    # -------------------------------------------------

    remaining = [
        place
        for place in places
        if place["name"] not in used
    ]

    day_keys = list(schedule.keys())

    for place in remaining:

        available_days = [
            day
            for day in day_keys
            if len(schedule[day])
            < MAX_PER_DAY
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

                    last_place = (
                        schedule[day][-1]
                    )

                    if (
                        last_place.get("lat")
                        is None
                        or last_place.get("lon")
                        is None
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

        # Fallback if coordinates aren't available
        if best_day is None:

            best_day = min(
                available_days,
                key=lambda d: len(
                    schedule[d]
                )
            )

        schedule[best_day].append(
            place
        )

        used.add(
            place["name"]
        )

    # -------------------------------------------------
    # Calculate travel distance between attractions
    # -------------------------------------------------

    for day, day_places in schedule.items():

        for index, place in enumerate(
            day_places
        ):

            if index == 0:

                place[
                    "travel_from_previous_km"
                ] = 0

                continue

            previous = day_places[
                index - 1
            ]

            if (
                previous.get("lat") is None
                or previous.get("lon") is None
                or place.get("lat") is None
                or place.get("lon") is None
            ):

                place[
                    "travel_from_previous_km"
                ] = None

                continue

            distance = haversine(
                previous["lat"],
                previous["lon"],
                place["lat"],
                place["lon"],
            )

            place[
                "travel_from_previous_km"
            ] = round(
                distance,
                2
            )

    # -------------------------------------------------
    # Diagnostics
    # -------------------------------------------------

    scheduled = sum(
        len(day)
        for day in schedule.values()
    )

    print(
        "Scheduled:",
        scheduled
    )

    print(
        "Available:",
        len(places)
    )

    print(
        "\nFINAL DAY SCHEDULE:"
    )

    for day, day_places in schedule.items():

        print(
            f"\nDAY {day}"
        )

        for place in day_places:

            print(
                place["name"],
                "→",
                place.get(
                    "travel_from_previous_km"
                ),
                "km"
            )

    return schedule