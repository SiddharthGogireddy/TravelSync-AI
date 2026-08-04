def plan_days(places, days):
    schedule = {}

    if days <= 0:
        return schedule

    per_day = max(1, len(places) // days)

    index = 0

    for day in range(1, days + 1):
        schedule[str(day)] = []

        for _ in range(per_day):
            if index >= len(places):
                break

            schedule[str(day)].append(places[index])
            index += 1

    while index < len(places):
        schedule[str(days)].append(places[index])
        index += 1

    return schedule