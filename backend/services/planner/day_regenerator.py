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

    # --------------------------------
    # Check if requested day exists
    # --------------------------------

    if day_key not in day_schedule:
        return trip

    current_day = day_schedule[day_key]

    # --------------------------------
    # Persistent activity targets
    # --------------------------------

    day_activity_targets = trip_data.setdefault(
        "day_activity_targets",
        {}
    )

    for day, places in day_schedule.items():

        if day in day_activity_targets:
            continue

        # If the day currently has activities,
        # use its current size as the target.
        if places:

            day_activity_targets[day] = len(
                places
            )

        else:

            # If the day is empty, try to recover
            # its original size from regeneration history.
            history = trip_data.get(
                "regeneration_history",
                {}
            )

            versions = history.get(
                day,
                []
            )

            previous_sizes = [
                len(version)
                for version in versions
                if version
            ]

            if previous_sizes:

                day_activity_targets[day] = (
                    previous_sizes[0]
                )

            else:

                # Safe fallback
                day_activity_targets[day] = 4

    # --------------------------------
    # Regeneration history
    # --------------------------------

    history = trip_data.setdefault(
        "regeneration_history",
        {}
    )

    previous_versions = history.setdefault(
        day_key,
        []
    )

    print(
        "REGEN HISTORY FOR DAY",
        day_key
    )

    print(
        previous_versions
    )

    # --------------------------------
    # Save current version
    # before replacing it
    # --------------------------------

    current_version = [
        place["name"].strip().lower()
        for place in current_day
    ]

    if current_version not in previous_versions:

        previous_versions.append(
            current_version
        )

    # --------------------------------
    # Every place previously used
    # for this day
    # --------------------------------

    previously_used = set()

    for version in previous_versions:

        previously_used.update(
            version
        )

    # --------------------------------
    # Places used on other days
    # --------------------------------

    used_elsewhere = set()

    for other_day, places in (
        day_schedule.items()
    ):

        if other_day == day_key:
            continue

        for place in places:

            used_elsewhere.add(
                place["name"]
                .strip()
                .lower()
            )

    # --------------------------------
    # Mandatory visits
    # --------------------------------

    mandatory_visits = trip_data.get(
        "mandatory_visits",
        []
    )

    mandatory_names = {
        visit["name"]
        .strip()
        .lower()
        for visit in mandatory_visits
        if visit.get("name")
    }

    # --------------------------------
    # Build candidates
    # --------------------------------

    candidates = []

    for place in trip_data.get(
        "places",
        []
    ):

        name = (
            place["name"]
            .strip()
            .lower()
        )

        # Don't reuse attractions that
        # appeared in previous versions
        # of this day.
        if name in previously_used:
            continue

        # Don't steal an attraction that
        # is currently scheduled elsewhere.
        if name in used_elsewhere:
            continue

        # Mandatory visits are handled
        # separately.
        if name in mandatory_names:
            continue

        candidates.append(
            place
        )

    # --------------------------------
    # Best remaining alternatives
    # --------------------------------

    candidates.sort(
        key=lambda place: (
            place.get(
                "score",
                0
            ),
            place.get(
                "match_count",
                0
            ),
        ),
        reverse=True,
    )

    # --------------------------------
    # Determine target activity count
    # --------------------------------

    number_of_places = (
        day_activity_targets.get(
            day_key,
            4
        )
    )

    print(
        "TARGET ACTIVITIES:",
        number_of_places
    )

    print(
        "NUMBER OF CANDIDATES:",
        len(candidates)
    )

    # --------------------------------
    # Select new activities
    # --------------------------------

    new_day = candidates[
        :number_of_places
    ]

    # --------------------------------
    # Replace the day
    # --------------------------------

    day_schedule[day_key] = new_day

    trip_data["day_schedule"] = (
        day_schedule
    )

    # --------------------------------
    # Save the new version
    # --------------------------------

    new_version = [
        place["name"]
        .strip()
        .lower()
        for place in new_day
    ]

    if new_version not in previous_versions:

        previous_versions.append(
            new_version
        )

    # --------------------------------
    # Recalculate budget
    # --------------------------------

    scheduled_activity_count = sum(
        len(day_places)
        for day_places in (
            day_schedule.values()
        )
    )

    trip_data["budget"] = (
        calculate_budget(
            trip_data["travelers"],
            trip_data["days"],
            trip_data["travel_mode"],
            trip_data["hotels"],
            trip_data["places"],
            scheduled_activity_count=(
                scheduled_activity_count
            ),
            total_budget=(
                trip_data["budget"][
                    "total_budget"
                ]
            ),
        )
    )

    print(
        ">>> regenerate_day RETURNING TRIP <<<"
    )

    return trip