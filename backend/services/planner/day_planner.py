def plan_days(
    places,
    days,
    mandatory_schedule=None,
    pace="Balanced",
):
    schedule = {}

    if days <= 0:
        return schedule

    pace_limits = {
        "Relaxed": 3,
        "Balanced": 4,
        "Fast": 5,
    }

    max_per_day = pace_limits.get(
        pace,
        4,
    )

    index = 0

    for day in range(1, days + 1):
        schedule[str(day)] = []

        for _ in range(max_per_day):
            if index >= len(places):
                break

            schedule[str(day)].append(
                places[index]
            )
            index += 1

    return schedule