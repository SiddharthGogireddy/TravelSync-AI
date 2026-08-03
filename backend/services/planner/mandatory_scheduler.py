def schedule_mandatory_visits(days, mandatory_visits):

    schedule = {
        day: []
        for day in range(1, days + 1)
    }

    remaining_day = 1

    for visit in mandatory_visits:

        if visit["day"] is not None:

            schedule[visit["day"]].append(
                visit["name"]
            )

        else:

            schedule[remaining_day].append(
                visit["name"]
            )

            remaining_day += 1

            if remaining_day > days:
                remaining_day = 1

    return schedule