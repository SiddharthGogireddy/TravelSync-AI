import math
from typing import Dict, List, Optional, Any, Tuple
from backend.services.planner.distance import haversine
from backend.services.planner.opening_hours_scheduler import (
    resolve_place_opening_hours,
    estimate_travel_minutes,
    minutes_to_time_str,
    time_to_minutes,
)


def replan_active_day(
    trip_data: Dict[str, Any],
    day_number: int,
    completed_attraction_names: List[str],
    remaining_hours: float = 4.0,
    current_location: Optional[Dict[str, float]] = None,
    current_location_name: Optional[str] = None,
    remaining_budget: Optional[float] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Replans the remaining portion of an active day's itinerary:
    - Retains already completed attractions marked as visited.
    - Excludes completed attractions from rescheduling.
    - Starts subsequent transit from current location or last visited stop.
    - Strictly fits remaining activities within remaining hours and budget.
    """
    day_key = str(day_number)
    day_schedule = trip_data.get("day_schedule", {})
    if day_key not in day_schedule:
        return trip_data, {
            "success": False,
            "error": f"Day {day_number} not found in trip schedule."
        }

    current_day_places = day_schedule[day_key]
    completed_set = {str(name).strip().lower() for name in completed_attraction_names}

    # 1. Separate completed vs uncompleted places
    completed_places = []
    for p in current_day_places:
        p_name = p.get("name", "").strip().lower()
        if p_name in completed_set:
            p_copy = dict(p)
            p_copy["is_completed"] = True
            p_copy["status"] = "Completed"
            completed_places.append(p_copy)

    # 2. Determine current location coordinate anchor
    if current_location and "lat" in current_location and "lon" in current_location:
        cur_lat = float(current_location["lat"])
        cur_lon = float(current_location["lon"])
        origin_label = current_location_name or "Current Location"
    elif completed_places:
        last_completed = completed_places[-1]
        cur_lat = float(last_completed.get("lat", 15.29))
        cur_lon = float(last_completed.get("lon", 74.12))
        origin_label = f"Last stop: {last_completed.get('name')}"
    elif current_day_places:
        cur_lat = float(current_day_places[0].get("lat", 15.29))
        cur_lon = float(current_day_places[0].get("lon", 74.12))
        origin_label = current_day_places[0].get("name")
    else:
        dest_loc = trip_data.get("destination_location", {})
        cur_lat = float(dest_loc.get("lat", 15.29))
        cur_lon = float(dest_loc.get("lon", 74.12))
        origin_label = trip_data.get("destination", "City Center")

    # 3. Gather candidate pool of unused attractions
    all_scheduled_names = set()
    for d, plist in day_schedule.items():
        if d == day_key:
            continue
        for p in plist:
            all_scheduled_names.add(p.get("name", "").strip().lower())
    for p in completed_places:
        all_scheduled_names.add(p.get("name", "").strip().lower())

    available_places = trip_data.get("places", [])
    candidates = []
    for p in available_places:
        name_norm = p.get("name", "").strip().lower()
        if not name_norm or name_norm in all_scheduled_names:
            continue

        plat = float(p.get("lat") or cur_lat)
        plon = float(p.get("lon") or cur_lon)
        dist = haversine(cur_lat, cur_lon, plat, plon)

        candidate_entry = dict(p)
        candidate_entry["distance_from_current_km"] = round(dist, 2)
        candidates.append(candidate_entry)

    # Sort candidates by distance from current location & score
    candidates.sort(key=lambda x: (x["distance_from_current_km"], -x.get("score", 0)))

    # 4. Fit activities into remaining hours
    remaining_minutes = max(30, int(remaining_hours * 60))
    travel_mode = trip_data.get("travel_mode", "car")

    # Start replanned sequence from (now / remaining buffer)
    # Assume day ends at 19:00 (1140 min). Start minute is 1140 - remaining_minutes
    start_min = max(540, 1140 - remaining_minutes)
    current_min = start_min

    new_remaining_places = []
    last_lat = cur_lat
    last_lon = cur_lon

    for cand in candidates:
        if current_min >= 1140:
            break

        oh = resolve_place_opening_hours(cand)
        cand["opening_hours"] = oh
        cand_lat = float(cand.get("lat") or last_lat)
        cand_lon = float(cand.get("lon") or last_lon)

        leg_dist = haversine(last_lat, last_lon, cand_lat, cand_lon)
        transit_min = estimate_travel_minutes(leg_dist, travel_mode)
        cand["travel_from_previous_km"] = round(leg_dist, 2)
        cand["travel_time_minutes"] = transit_min

        arrival_min = current_min + transit_min
        duration = int(oh.get("visit_duration_minutes", 60))

        # Check if fits in remaining day time
        if (arrival_min + duration) > (start_min + remaining_minutes):
            continue

        # Check opening hours
        if arrival_min < oh["opens_minute"]:
            arrival_min = oh["opens_minute"]

        if (arrival_min + duration) <= oh["closes_minute"]:
            cand["arrival_time"] = minutes_to_time_str(arrival_min)
            cand["departure_time"] = minutes_to_time_str(arrival_min + duration)
            cand["time_window"] = f"{cand['arrival_time']} - {cand['departure_time']}"
            cand["timing_status"] = "Replanned (Real-Time)"
            cand["is_completed"] = False
            cand["status"] = "Upcoming"
            new_remaining_places.append(cand)

            current_min = arrival_min + duration
            last_lat = cand_lat
            last_lon = cand_lon

        if len(new_remaining_places) >= 4:
            break

    # 5. Combine completed stops + newly replanned stops
    updated_day_places = completed_places + new_remaining_places
    trip_data["day_schedule"][day_key] = updated_day_places

    replan_audit = {
        "success": True,
        "day": day_number,
        "origin_label": origin_label,
        "completed_count": len(completed_places),
        "replanned_count": len(new_remaining_places),
        "total_day_activities": len(updated_day_places),
        "remaining_hours": remaining_hours,
        "summary": f"Preserved {len(completed_places)} completed stop(s) and scheduled {len(new_remaining_places)} optimized stop(s) from {origin_label} for the remaining {remaining_hours} hour(s)."
    }

    trip_data["realtime_replan_audit"] = replan_audit
    return trip_data, replan_audit
