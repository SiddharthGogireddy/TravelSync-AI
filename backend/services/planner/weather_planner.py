import math
from typing import Dict, List, Optional, Any, Tuple
from backend.services.planner.distance import haversine


INDOOR_KEYWORDS = [
    "museum", "gallery", "aquarium", "planetarium", "mall", "market",
    "theatre", "theater", "cinema", "palace", "temple", "church", "cathedral",
    "mosque", "indoor", "art", "science", "bazaar", "heritage home"
]

OUTDOOR_KEYWORDS = [
    "park", "garden", "beach", "lake", "zoo", "stadium", "monument",
    "viewpoint", "waterfall", "fort", "hill", "outdoor", "peak", "trek",
    "cliff", "island", "safari", "valley", "spring"
]


def classify_weather(weather_code: int, max_temp: Optional[float] = None) -> str:
    """Classifies weather condition into simplified category."""
    if weather_code >= 95:
        return "storm"
    if weather_code in [61, 63, 65, 80, 81, 82] or weather_code >= 80:
        return "rain"
    if max_temp is not None and max_temp >= 38.0:
        return "extreme_heat"
    if weather_code >= 50 or weather_code == 3:
        return "cloudy"
    return "clear"


def classify_weather_condition(day_weather: Dict[str, Any]) -> Tuple[str, bool, str]:
    """
    Returns (condition_type, is_severe, explanation).
    Severe conditions trigger protective replanning.
    """
    code = int(day_weather.get("weather_code", 0))
    temp = day_weather.get("max_temp")
    temp_val = float(temp) if temp is not None else None

    cond = classify_weather(code, temp_val)
    if cond == "storm":
        return "storm", True, f"Severe thunderstorms forecasted (Code {code})"
    if cond == "rain":
        return "rain", True, f"Heavy rainfall forecasted (Code {code})"
    if cond == "extreme_heat":
        return "extreme_heat", True, f"Extreme heat alert ({temp_val}°C)"
    if cond == "cloudy":
        return "cloudy", False, "Cloudy conditions, safe for outdoor activities"
    return "clear", False, "Clear and favorable weather"


def is_outdoor_place(place: Dict[str, Any]) -> bool:
    category = (place.get("category") or "").lower()
    name = (place.get("name") or "").lower()
    combined = f"{category} {name}"

    # If it explicitly matches indoor keywords, prioritize indoor
    if any(k in combined for k in INDOOR_KEYWORDS):
        return False

    return any(k in combined for k in OUTDOOR_KEYWORDS)


def is_indoor_place(place: Dict[str, Any]) -> bool:
    return not is_outdoor_place(place)


def recalculate_day_transit_distances(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Recalculates sequential travel distances between stops on a day."""
    if not places:
        return []

    for i, place in enumerate(places):
        if i == 0:
            place["travel_from_previous_km"] = 0.0
        else:
            prev = places[i - 1]
            if prev.get("lat") and prev.get("lon") and place.get("lat") and place.get("lon"):
                dist = haversine(prev["lat"], prev["lon"], place["lat"], place["lon"])
                place["travel_from_previous_km"] = round(dist, 2)
            else:
                place["travel_from_previous_km"] = 1.5

    return places


def replan_trip_for_weather(
    day_schedule: Dict[str, List[Dict[str, Any]]],
    weather_summary: Optional[List[Dict[str, Any]]],
    available_places: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Adapts itinerary for severe weather:
    1. Detects rain, storms, or extreme heat.
    2. Swaps activities with favorable days where possible.
    3. Replaces outdoor sights with indoor alternatives when swapping isn't feasible.
    4. Recalculates travel distances for modified routes.
    5. Explains replanning decisions clearly to the user.
    """
    if not weather_summary or not day_schedule:
        return day_schedule, {
            "has_weather_replan": False,
            "adverse_days_count": 0,
            "decisions": [],
            "summary": "No severe weather detected. Itinerary scheduled normally."
        }

    updated_schedule = {day: list(places) for day, places in day_schedule.items()}
    days = list(updated_schedule.keys())

    used_names = set()
    for plist in updated_schedule.values():
        for p in plist:
            used_names.add(p.get("name", "").lower())

    indoor_pool = [
        p for p in (available_places or [])
        if p.get("name", "").lower() not in used_names and is_indoor_place(p)
    ]

    decisions = []
    adverse_days = 0

    for idx, day_number in enumerate(days):
        if idx >= len(weather_summary):
            break

        day_weather = weather_summary[idx]
        cond, is_severe, reason = classify_weather_condition(day_weather)

        if not is_severe:
            continue

        adverse_days += 1
        current_places = list(updated_schedule[day_number])
        outdoor_activities = [p for p in current_places if is_outdoor_place(p)]

        if not outdoor_activities:
            continue

        new_day_places = []
        for place in current_places:
            if not is_outdoor_place(place):
                new_day_places.append(place)
                continue

            # This place is outdoor on a severe weather day!
            # Strategy 1: Attempt to swap with an indoor activity on a clear/favorable future or past day
            swapped = False
            for other_idx, other_day in enumerate(days):
                if other_day == day_number or other_idx >= len(weather_summary):
                    continue

                other_cond, other_severe, _ = classify_weather_condition(weather_summary[other_idx])
                if not other_severe:
                    # Look for an indoor activity on that favorable day to swap
                    other_places = updated_schedule[other_day]
                    for other_p_idx, other_p in enumerate(other_places):
                        if is_indoor_place(other_p):
                            # Swap them!
                            other_places[other_p_idx] = place
                            new_day_places.append(other_p)
                            swapped = True
                            decisions.append({
                                "day": day_number,
                                "date": day_weather.get("date"),
                                "condition": cond,
                                "action": "swapped_activities",
                                "original_attraction": place.get("name"),
                                "swapped_with": other_p.get("name"),
                                "target_day": other_day,
                                "explanation": f"Swapped outdoor '{place.get('name')}' with indoor '{other_p.get('name')}' on Day {other_day} due to {reason.lower()} on Day {day_number}."
                            })
                            break
                if swapped:
                    break

            if swapped:
                continue

            # Strategy 2: If cannot swap, replace with an indoor alternative from pool
            if indoor_pool:
                replacement = indoor_pool.pop(0)
                new_day_places.append(replacement)
                used_names.add(replacement.get("name", "").lower())
                decisions.append({
                    "day": day_number,
                    "date": day_weather.get("date"),
                    "condition": cond,
                    "action": "replaced_with_indoor",
                    "original_attraction": place.get("name"),
                    "replacement": replacement.get("name"),
                    "explanation": f"Replaced outdoor attraction '{place.get('name')}' with indoor alternative '{replacement.get('name')}' due to {reason.lower()} on Day {day_number}."
                })
            else:
                # Keep original with weather advisory
                place["weather_advisory"] = f"Caution: Outdoor activity scheduled during {cond}."
                new_day_places.append(place)
                decisions.append({
                    "day": day_number,
                    "date": day_weather.get("date"),
                    "condition": cond,
                    "action": "advisory_issued",
                    "original_attraction": place.get("name"),
                    "explanation": f"Kept '{place.get('name')}' with an advisory as no suitable indoor alternatives were available."
                })

        # Recalculate route distances after substitutions
        updated_schedule[day_number] = recalculate_day_transit_distances(new_day_places)

    has_replan = len(decisions) > 0
    summary_text = (
        f"{len(decisions)} weather adaptation decision(s) made across {adverse_days} adverse weather day(s)."
        if has_replan
        else "All days forecast favorable weather. No replanning necessary."
    )

    replan_report = {
        "has_weather_replan": has_replan,
        "adverse_days_count": adverse_days,
        "decisions": decisions,
        "summary": summary_text,
    }

    return updated_schedule, replan_report


def adjust_schedule_for_weather(day_schedule, weather_summary):
    """Backward compatibility wrapper."""
    updated, _ = replan_trip_for_weather(day_schedule, weather_summary)
    return updated