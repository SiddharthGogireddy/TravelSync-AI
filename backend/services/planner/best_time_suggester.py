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

def suggest_best_time(place):
    category = place.get("category", "").lower()

    if "museum" in category:
        return {
            "best_time": "10:00 AM - 1:00 PM",
            "reason": "Museums are generally better suited for daytime visits."
        }

    if "park" in category or "garden" in category:
        return {
            "best_time": "5:00 PM - 7:00 PM",
            "reason": "Outdoor locations are generally more comfortable in the evening."
        }

    if "temple" in category or "religious" in category:
        return {
            "best_time": "6:00 AM - 9:00 AM",
            "reason": "Morning visits are generally suitable for religious attractions."
        }

    if "beach" in category:
        return {
            "best_time": "5:00 PM - 7:00 PM",
            "reason": "Evening is generally more suitable for beach visits."
        }

    return {
        "best_time": "10:00 AM - 5:00 PM",
        "reason": "Daytime is a general suitable period for visiting this attraction."
    }