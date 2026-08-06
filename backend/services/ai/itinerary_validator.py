def validate_itinerary(itinerary: str, trip_data: dict):
    """
    Checks whether the generated itinerary satisfies
    important planning constraints.
    """

    errors = []

    # Check mandatory visits
    for day, visits in trip_data["mandatory_schedule"].items():
        for visit in visits:
            if visit.lower() not in itinerary.lower():
                errors.append(
                    f"Mandatory visit missing: {visit} (Day {day})"
                )

    # Check number of days
    day_count = itinerary.lower().count("day ")

    if day_count < trip_data["days"]:
        errors.append("Some days are missing.")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }