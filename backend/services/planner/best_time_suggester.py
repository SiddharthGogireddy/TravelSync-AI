from datetime import datetime

# Basic weekday mapping
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def suggest_best_days(weather_data):
    """
    weather_data: list of dicts with date + weather_code
    """

    best_days = []

    for day in weather_data:
        date_str = day["date"]
        weather_code = day["weather_code"]

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = WEEKDAYS[date_obj.weekday()]

        # Skip weekends
        if weekday in ["Saturday", "Sunday"]:
            continue

        # Skip bad weather (thunderstorm / heavy rain)
        if weather_code >= 80:
            continue

        best_days.append(weekday)

    return {
        "best_days": best_days[:3],  # limit
        "reason": "Weekdays with better weather conditions"
    }