import math
from typing import Dict, List, Optional, Any, Tuple


# Speed in km/h for urban/inter-attraction travel
SPEED_MAP = {
    "car": 35.0,
    "bus": 22.0,
    "train": 40.0,
    "flight": 500.0,
    "walking": 4.5,
    "bicycle": 15.0,
}


def time_to_minutes(time_str: str) -> int:
    """Converts 'HH:MM' (24-hr) to minutes from midnight."""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 540  # Default 09:00 AM


def minutes_to_time_str(minutes: int) -> str:
    """Converts minutes from midnight to 'hh:mm AM/PM'."""
    minutes = int(minutes) % (24 * 60)
    hour = minutes // 60
    minute = minutes % 60
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if 1 <= hour <= 12 else (12 if hour == 0 else hour - 12)
    return f"{display_hour:02d}:{minute:02d} {period}"


def resolve_place_opening_hours(place: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determines opening & closing hours and recommended visit duration
    based on place category, name, or existing metadata.
    """
    if place.get("opening_hours") and isinstance(place["opening_hours"], dict):
        oh = place["opening_hours"]
        if "opens_minute" in oh and "closes_minute" in oh:
            return oh

    category = (place.get("category") or "").lower()
    name = (place.get("name") or "").lower()

    # Default category timings
    if any(k in category or k in name for k in ["museum", "gallery", "art"]):
        opens = "10:00"
        closes = "17:30"
        duration = 105
        closed_days = ["Monday"]
    elif any(k in category or k in name for k in ["fort", "palace", "monument", "historic", "heritage", "archaeol"]):
        opens = "09:00"
        closes = "17:30"
        duration = 90
        closed_days = []
    elif any(k in category or k in name for k in ["park", "garden", "nature", "lake", "waterfall", "botanic"]):
        opens = "06:30"
        closes = "19:00"
        duration = 75
        closed_days = []
    elif any(k in category or k in name for k in ["temple", "church", "mosque", "religion", "chapel", "shrine"]):
        opens = "06:00"
        closes = "20:30"
        duration = 60
        closed_days = []
    elif any(k in category or k in name for k in ["beach", "coast", "promenade"]):
        opens = "06:00"
        closes = "21:00"
        duration = 90
        closed_days = []
    elif any(k in category or k in name for k in ["food", "restaurant", "cafe", "dhaba", "dining", "bar"]):
        opens = "11:30"
        closes = "23:00"
        duration = 60
        closed_days = []
    elif any(k in category or k in name for k in ["mall", "shop", "market", "bazaar"]):
        opens = "10:30"
        closes = "21:30"
        duration = 90
        closed_days = []
    elif any(k in category or k in name for k in ["nightlife", "pub", "club"]):
        opens = "19:00"
        closes = "02:00"
        duration = 120
        closed_days = []
    else:
        opens = "09:00"
        closes = "18:00"
        duration = 75
        closed_days = []

    opens_min = time_to_minutes(opens)
    closes_min = time_to_minutes(closes)
    # Handle overnight (e.g. 19:00 to 02:00)
    if closes_min < opens_min:
        closes_min += 24 * 60

    return {
        "opens": opens,
        "closes": closes,
        "opens_minute": opens_min,
        "closes_minute": closes_min,
        "display": f"{minutes_to_time_str(opens_min)} - {minutes_to_time_str(closes_min)}",
        "visit_duration_minutes": duration,
        "closed_days": closed_days,
    }


def estimate_travel_minutes(distance_km: float, travel_mode: str) -> int:
    """Calculates realistic transit time between stops."""
    if not distance_km or distance_km <= 0:
        return 10  # Minimum transition / staging buffer

    speed = SPEED_MAP.get(str(travel_mode).lower(), 30.0)
    transit_mins = (distance_km / speed) * 60.0
    # Add 5 mins parking / embarkation buffer
    return max(10, int(math.ceil(transit_mins + 5)))


def schedule_day_opening_hours(
    places: List[Dict[str, Any]],
    travel_mode: str = "car",
    day_start_hour: str = "09:00",
    available_alternatives: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Schedules attractions for a single day strictly within their opening hours,
    accounting for travel time before arrival. If an attraction cannot fit,
    attempts to swap with a later-closing candidate or replan with an alternative.
    """
    if not places:
        return [], []

    scheduled_results: List[Dict[str, Any]] = []
    replan_notes: List[str] = []

    current_minute = time_to_minutes(day_start_hour)
    candidates_pool = list(places)
    unused_alternatives = list(available_alternatives or [])

    while candidates_pool:
        place = candidates_pool.pop(0)
        oh = resolve_place_opening_hours(place)
        place["opening_hours"] = oh

        dist = float(place.get("travel_from_previous_km") or 0.0)
        travel_mins = estimate_travel_minutes(dist, travel_mode)
        place["travel_time_minutes"] = travel_mins

        estimated_arrival = current_minute + travel_mins
        duration = int(oh.get("visit_duration_minutes", 75))

        # Check if arriving before opening time
        if estimated_arrival < oh["opens_minute"]:
            # Arrived early: wait until attraction opens
            visit_start = oh["opens_minute"]
            visit_end = visit_start + duration
        else:
            visit_start = estimated_arrival
            visit_end = visit_start + duration

        # Check if fits before closing time
        if visit_end <= oh["closes_minute"]:
            # Fits perfectly within opening hours!
            place["arrival_time"] = minutes_to_time_str(visit_start)
            place["departure_time"] = minutes_to_time_str(visit_end)
            place["time_window"] = f"{minutes_to_time_str(visit_start)} - {minutes_to_time_str(visit_end)}"
            place["is_open_on_arrival"] = True
            place["timing_status"] = "Open & Scheduled"
            scheduled_results.append(place)
            current_minute = visit_end
        else:
            # Attraction is closed or cannot fit before closing!
            # 1. Try finding a remaining place in candidates_pool that closes later
            found_swap = False
            for i, other in enumerate(candidates_pool):
                other_oh = resolve_place_opening_hours(other)
                other_dur = int(other_oh.get("visit_duration_minutes", 75))
                if (estimated_arrival + other_dur) <= other_oh["closes_minute"]:
                    # Swap candidate
                    candidates_pool.insert(0, other)
                    candidates_pool.pop(i + 1)
                    candidates_pool.append(place)
                    found_swap = True
                    replan_notes.append(
                        f"Reordered '{other.get('name')}' ahead of '{place.get('name')}' to respect open hours."
                    )
                    break

            if found_swap:
                continue

            # 2. Try replacing with an unused alternative that is open
            replacement_found = False
            for alt_idx, alt_place in enumerate(unused_alternatives):
                alt_oh = resolve_place_opening_hours(alt_place)
                alt_dur = int(alt_oh.get("visit_duration_minutes", 75))
                if (estimated_arrival + alt_dur) <= alt_oh["closes_minute"]:
                    alt_place["opening_hours"] = alt_oh
                    alt_place["travel_from_previous_km"] = dist
                    alt_place["travel_time_minutes"] = travel_mins
                    alt_place["arrival_time"] = minutes_to_time_str(visit_start)
                    alt_place["departure_time"] = minutes_to_time_str(visit_start + alt_dur)
                    alt_place["time_window"] = f"{minutes_to_time_str(visit_start)} - {minutes_to_time_str(visit_start + alt_dur)}"
                    alt_place["is_open_on_arrival"] = True
                    alt_place["timing_status"] = "Open & Scheduled (Replanned)"
                    scheduled_results.append(alt_place)
                    current_minute = visit_start + alt_dur
                    unused_alternatives.pop(alt_idx)
                    replacement_found = True
                    replan_notes.append(
                        f"Replanned: Replaced '{place.get('name')}' with '{alt_place.get('name')}' as the original would be closed."
                    )
                    break

            if not replacement_found:
                # If cannot swap or replace, schedule with adjusted window & note
                adjusted_end = min(visit_end, oh["closes_minute"])
                place["arrival_time"] = minutes_to_time_str(visit_start)
                place["departure_time"] = minutes_to_time_str(adjusted_end)
                place["time_window"] = f"{minutes_to_time_str(visit_start)} - {minutes_to_time_str(adjusted_end)}"
                place["is_open_on_arrival"] = False
                place["timing_status"] = "Limited Hours / Adjusted"
                scheduled_results.append(place)
                current_minute = adjusted_end
                replan_notes.append(
                    f"Adjusted visit window for '{place.get('name')}' to end at closing time ({minutes_to_time_str(oh['closes_minute'])})."
                )

    from backend.services.planner.distance import haversine

    for idx, p in enumerate(scheduled_results):
        if idx == 0:
            p["travel_from_previous_km"] = None
            p["travel_time_minutes"] = 0
        else:
            prev = scheduled_results[idx - 1]
            lat1, lon1 = prev.get("lat"), prev.get("lon")
            lat2, lon2 = p.get("lat"), p.get("lon")
            if (
                lat1 is not None and lon1 is not None
                and lat2 is not None and lon2 is not None
                and (lat1 != 0 or lon1 != 0) and (lat2 != 0 or lon2 != 0)
            ):
                d = round(haversine(lat1, lon1, lat2, lon2), 2)
                if d > 0.05:
                    p["travel_from_previous_km"] = d
                    p["travel_time_minutes"] = estimate_travel_minutes(d, travel_mode)
                else:
                    p["travel_from_previous_km"] = None
                    p["travel_time_minutes"] = 10
            else:
                p["travel_from_previous_km"] = None
                p["travel_time_minutes"] = 10

    return scheduled_results, replan_notes


def apply_opening_hours_to_schedule(
    day_schedule: Dict[str, List[Dict[str, Any]]],
    travel_mode: str = "car",
    available_places: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
    """
    Applies opening-hours scheduling across all days of the trip itinerary.
    """
    updated_schedule: Dict[str, List[Dict[str, Any]]] = {}
    all_notes: List[str] = []

    used_names = set()
    for places in day_schedule.values():
        for p in places:
            used_names.add(p.get("name", "").lower())

    # Filter unused candidates for replacement
    unused_pool = [
        p for p in (available_places or [])
        if p.get("name", "").lower() not in used_names
    ]

    for day_key, places in day_schedule.items():
        # Religious / beach mornings might start earlier, but default is 09:00 AM
        first_cat = (places[0].get("category") or "").lower() if places else ""
        day_start = "08:00" if any(k in first_cat for k in ["temple", "religion", "beach"]) else "09:00"

        scheduled_day_places, day_notes = schedule_day_opening_hours(
            places=places,
            travel_mode=travel_mode,
            day_start_hour=day_start,
            available_alternatives=unused_pool,
        )
        updated_schedule[day_key] = scheduled_day_places
        if day_notes:
            all_notes.extend([f"Day {day_key}: {n}" for n in day_notes])

    return updated_schedule, all_notes
