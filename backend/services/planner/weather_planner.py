def classify_weather(weather_code):
    if weather_code >= 95:
        return "storm"

    if weather_code >= 80:
        return "rain"

    if weather_code >= 50:
        return "cloudy"

    return "clear"

def is_outdoor_place(place):
    category = place.get("category", "").lower()
    name = place.get("name", "").lower()

    outdoor_keywords = [
        "park",
        "garden",
        "beach",
        "lake",
        "zoo",
        "stadium",
        "monument",
        "viewpoint",
        "waterfall",
        "fort",
        "hill",
        "outdoor",
    ]

    text = f"{category} {name}"

    words = text.replace("-", " ").split()

    result = any(
        keyword in words
        for keyword in outdoor_keywords
    )

    print(
        "WEATHER CHECK:",
        place["name"],
        "|",
        category,
        "| outdoor:",
        result,
    )

    return result
def adjust_schedule_for_weather(day_schedule, weather_summary):
    if not weather_summary:
        return day_schedule

    weather_by_date = {
        day["date"]: classify_weather(day["weather_code"])
        for day in weather_summary
    }

    days = list(day_schedule.keys())

    # Weather is matched to itinerary days in order
    for index, day_number in enumerate(days):
        if index >= len(weather_summary):
            break

        weather = weather_by_date.get(
            weather_summary[index]["date"],
            "clear"
        )

        if weather not in ["rain", "storm"]:
            continue

        outdoor_places = []
        indoor_places = []

        for place in day_schedule[day_number]:
            if is_outdoor_place(place):
                outdoor_places.append(place)
            else:
                indoor_places.append(place)

        # Keep indoor activities on bad-weather days
        day_schedule[day_number] = indoor_places

        # Move outdoor activities to the next suitable day
        for place in outdoor_places:
            moved = False
            max_per_day = 4

            for other_day in days:
                if other_day == day_number:
                    continue

                other_index = days.index(other_day)

                if other_index >= len(weather_summary):
                    continue

                other_weather = classify_weather(
                    weather_summary[other_index]["weather_code"]
                )
                if (
                    other_weather in ["clear", "cloudy"]
                    and len(day_schedule[other_day]) < max_per_day
                ):
                    day_schedule[other_day].append(place)
                    moved = True
                    break

            # If no suitable day exists, keep the attraction
            if not moved:
                day_schedule[day_number].append(place)

    return day_schedule