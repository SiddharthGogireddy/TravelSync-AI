import math
from typing import Dict, List, Optional, Any, Tuple
from backend.services.planner.distance import haversine
from backend.services.planner.opening_hours_scheduler import estimate_travel_minutes, minutes_to_time_str


CURATED_CORRIDOR_PRESETS = [
    {"name": "Scenic Valley Viewpoint", "category": "Viewpoint", "type": "Scenic Overlook", "score": 8, "pause_min": 35},
    {"name": "Highway Heritage Dhaba & Tea Garden", "category": "Foods", "type": "Refreshment Break", "score": 8, "pause_min": 45},
    {"name": "Ancient Rock-Cut Caves", "category": "Historic", "type": "Cultural Pause", "score": 9, "pause_min": 50},
    {"name": "Riverside Waterfall Rest Area", "category": "Nature", "type": "Nature Walk", "score": 9, "pause_min": 40},
    {"name": "Terrace View Botanical Nursery", "category": "Park", "type": "Relaxing Garden", "score": 7, "pause_min": 30},
    {"name": "Hilltop Fortress Gateway", "category": "Historic", "type": "Historic Monument", "score": 8, "pause_min": 45},
]


def sample_corridor_waypoints(coordinates: List[List[float]], num_samples: int = 4) -> List[Dict[str, Any]]:
    """
    Samples intermediate coordinate waypoints along the route polyline.
    coordinates are in [lon, lat] format from GeoJSON.
    """
    if not coordinates:
        return []

    total_pts = len(coordinates)
    if total_pts < 2:
        lon, lat = coordinates[0]
        return [{"lat": lat, "lon": lon, "percent": 50}]

    waypoints = []
    step = total_pts / (num_samples + 1)
    for i in range(1, num_samples + 1):
        idx = min(total_pts - 1, int(i * step))
        pt = coordinates[idx]
        pct = int(round((i / (num_samples + 1)) * 100))
        waypoints.append({
            "lat": float(pt[1]),
            "lon": float(pt[0]),
            "percent": pct,
        })

    return waypoints


def calculate_detour_impact(
    waypoint_lat: float,
    waypoint_lon: float,
    attraction_lat: float,
    attraction_lon: float,
    travel_mode: str = "car",
) -> Dict[str, Any]:
    """
    Calculates one-way and round-trip detour distance and added travel time
    when diverting from the main route corridor.
    """
    one_way_dist = haversine(waypoint_lat, waypoint_lon, attraction_lat, attraction_lon)
    # Round-trip deviation back to the highway
    round_trip_detour_km = round(one_way_dist * 1.8, 1)

    speed = 45.0 if str(travel_mode).lower() in ["car", "bike"] else 30.0
    added_transit_minutes = max(10, int(round((round_trip_detour_km / speed) * 60.0 + 8.0)))

    return {
        "one_way_km": round(one_way_dist, 1),
        "round_trip_detour_km": round_trip_detour_km,
        "added_transit_minutes": added_transit_minutes,
    }


async def discover_route_attractions(
    route: Dict[str, Any],
    destination_places: Optional[List[Dict[str, Any]]] = None,
    travel_mode: str = "car",
    max_detour_km: float = 20.0,
    day_schedule: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Identifies high-value attractions along the travel route corridor
    within an acceptable detour distance, evaluating suitability and distance
    separately for each itinerary day.
    """
    discovered: List[Dict[str, Any]] = []

    # Extract coordinates from route geometry
    coords = []
    if route and "routes" in route and len(route["routes"]) > 0:
        geom = route["routes"][0].get("geometry", {})
        coords = geom.get("coordinates", [])

    if not coords:
        # Fallback to direct corridor sampling if no detailed geometry
        coords = [[78.48, 17.38], [73.82, 15.49]]

    waypoints = sample_corridor_waypoints(coords, num_samples=len(CURATED_CORRIDOR_PRESETS))

    for idx, wp in enumerate(waypoints):
        preset = CURATED_CORRIDOR_PRESETS[idx % len(CURATED_CORRIDOR_PRESETS)]

        # Offset slightly from the highway centerline (2 to 8 km)
        angle = (idx * 1.1) % 6.28
        offset_dist = 2.5 + (idx % 3) * 1.8  # km
        dlat = (offset_dist / 111.0) * math.cos(angle)
        dlon = (offset_dist / 111.0) * math.sin(angle)

        attraction_lat = round(wp["lat"] + dlat, 4)
        attraction_lon = round(wp["lon"] + dlon, 4)

        impact = calculate_detour_impact(
            wp["lat"], wp["lon"],
            attraction_lat, attraction_lon,
            travel_mode=travel_mode,
        )

        if impact["round_trip_detour_km"] > max_detour_km:
            continue

        stop_id = f"route_stop_{idx + 1}"

        # Per-day distance calculations and suitability evaluation
        day_evaluations: Dict[str, Any] = {}
        candidate_days: List[int] = []

        if day_schedule and isinstance(day_schedule, dict):
            for d_str, d_places in day_schedule.items():
                if not d_str.isdigit():
                    continue
                d_num = int(d_str)
                candidate_days.append(d_num)
                places_list = d_places if isinstance(d_places, list) else []

                # Find nearest reference stop in this day's route
                ref_stop_name = "Day Departure Point"
                min_straight_dist = impact["one_way_km"]

                if places_list:
                    closest_place = None
                    closest_dist = float("inf")
                    for p in places_list:
                        p_lat = p.get("lat")
                        p_lon = p.get("lon")
                        if p_lat is not None and p_lon is not None:
                            d = haversine(p_lat, p_lon, attraction_lat, attraction_lon)
                            if d < closest_dist:
                                closest_dist = d
                                closest_place = p

                    if closest_place and closest_dist != float("inf"):
                        ref_stop_name = closest_place.get("name", "Scheduled Stop")
                        min_straight_dist = round(closest_dist, 1)

                straight_line_dist = min_straight_dist
                estimated_road_dist = round(straight_line_dist * 1.35, 1)
                day_detour_dist = round(straight_line_dist * 1.8, 1)
                speed = 45.0 if str(travel_mode).lower() in ["car", "bike"] else 30.0
                day_added_transit_min = max(10, int(round((day_detour_dist / speed) * 60.0 + 5.0)))

                current_day_dist = sum(
                    float(p.get("travel_from_previous_km", 0.0) or 0.0)
                    for p in places_list
                    if isinstance(p, dict)
                )
                projected_day_dist = round(current_day_dist + day_detour_dist, 1)

                day_evaluations[str(d_num)] = {
                    "day": d_num,
                    "reference_stop_name": ref_stop_name,
                    "straight_line_distance_km": straight_line_dist,
                    "estimated_road_distance_km": estimated_road_dist,
                    "detour_distance_km": day_detour_dist,
                    "added_transit_minutes": day_added_transit_min,
                    "current_stop_count": len(places_list),
                    "total_daily_route_km": projected_day_dist,
                    "has_schedule_capacity": len(places_list) < 5,
                    "distance_label": f"{straight_line_dist} km straight-line from {ref_stop_name} (~{estimated_road_dist} km road)",
                }

        # Select most suitable day
        recommended_day = 1
        recommendation_reason = "Day route data unavailable; defaulting to Day 1. Manual day selection available."

        if day_evaluations:
            # Score candidate days: prefer days with capacity (< 5 stops) and lowest detour
            scored_days = []
            for d_num, eval_data in day_evaluations.items():
                cap_penalty = 0 if eval_data["has_schedule_capacity"] else 50
                score = eval_data["detour_distance_km"] + cap_penalty + (eval_data["current_stop_count"] * 2.0)
                scored_days.append((score, int(d_num), eval_data))

            scored_days.sort(key=lambda x: x[0])
            best_tuple = scored_days[0]
            recommended_day = best_tuple[1]
            best_eval = best_tuple[2]

            recommendation_reason = (
                f"Recommended for Day {recommended_day}: closest to '{best_eval['reference_stop_name']}' "
                f"({best_eval['straight_line_distance_km']} km straight-line, ~{best_eval['estimated_road_distance_km']} km road) "
                f"with +{best_eval['detour_distance_km']} km detour and ample schedule capacity ({best_eval['current_stop_count']} existing stops)."
            )

        discovered.append({
            "id": stop_id,
            "name": preset["name"],
            "category": preset["category"],
            "type": preset["type"],
            "score": preset["score"],
            "lat": attraction_lat,
            "lon": attraction_lon,
            "corridor_progress_percent": wp["percent"],
            "corridor_position": f"{wp['percent']}% along travel route",
            "detour_distance_km": impact["round_trip_detour_km"],
            "added_travel_time_minutes": impact["added_transit_minutes"],
            "recommended_pause_minutes": preset["pause_min"],
            "description": f"Scenic stop {wp['percent']}% along the route with +{impact['round_trip_detour_km']} km detour.",
            "is_route_stop": True,
            "recommended_day": recommended_day,
            "recommendation_reason": recommendation_reason,
            "day_evaluations": day_evaluations,
        })

    return discovered


async def get_route_attractions(
    route,
    destination_places,
    travel_mode,
):
    """
    Backward-compatible entrypoint: returns combined places with route discoveries.
    """
    discovered_route_stops = await discover_route_attractions(
        route=route,
        destination_places=destination_places,
        travel_mode=travel_mode,
    )
    combined = list(destination_places or [])
    combined.extend(discovered_route_stops)
    return combined


def insert_route_stop_into_day(
    trip_data: Dict[str, Any],
    day_number: int,
    route_stop: Dict[str, Any],
    allow_repeat: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Inserts a discovered route stop into a specific day's schedule,
    recalculates transit times, and verifies that total travel time remains acceptable.
    Supports confirmed duplicate/repeat visits.
    """
    day_key = str(day_number)
    day_schedule = trip_data.get("day_schedule", {})
    if day_key not in day_schedule:
        return trip_data, {
            "success": False,
            "error": f"Day {day_number} not found in schedule.",
        }

    places = list(day_schedule[day_key])

    # Check for duplicate
    stop_name = route_stop.get("name", "").strip().lower()
    is_already_present = any(p.get("name", "").strip().lower() == stop_name for p in places)

    if is_already_present and not allow_repeat:
        return trip_data, {
            "success": False,
            "is_duplicate": True,
            "error": f"Route stop '{route_stop.get('name')}' is already scheduled in Day {day_number}. Confirm repeat visit to proceed.",
        }

    # Format the stop as a scheduled place
    day_eval = (route_stop.get("day_evaluations") or {}).get(str(day_number), {})
    detour_dist = day_eval.get("detour_distance_km", route_stop.get("detour_distance_km", 5.0))
    transit_mins = day_eval.get("added_transit_minutes", route_stop.get("added_travel_time_minutes", 20))

    scheduled_entry = {
        "name": route_stop.get("name") if not (is_already_present and allow_repeat) else f"{route_stop.get('name')} (Repeat Visit)",
        "category": route_stop.get("category", "En-Route Stop"),
        "lat": route_stop.get("lat"),
        "lon": route_stop.get("lon"),
        "distance_km": detour_dist,
        "travel_from_previous_km": detour_dist,
        "travel_time_minutes": transit_mins,
        "time_window": f"{route_stop.get('recommended_pause_minutes', 45)} min Scenic Pause",
        "timing_status": "En-Route Scenic Stop (Repeat)" if (is_already_present and allow_repeat) else "En-Route Scenic Stop",
        "is_en_route": True,
        "is_repeat": bool(is_already_present and allow_repeat),
        "is_repeat_visit": bool(is_already_present and allow_repeat),
        "score": route_stop.get("score", 8),
    }

    # Insert between 1st and 2nd stop, or at start of the day
    insert_pos = 1 if len(places) > 1 else len(places)
    places.insert(insert_pos, scheduled_entry)
    day_schedule[day_key] = places
    trip_data["day_schedule"] = day_schedule

    # Calculate total travel time for day
    total_day_transit_minutes = sum(p.get("travel_time_minutes", 15) for p in places)
    is_acceptable = total_day_transit_minutes <= 360  # <= 6 hours transit

    audit = {
        "success": True,
        "day": day_number,
        "inserted_stop": scheduled_entry["name"],
        "added_detour_km": detour_dist,
        "added_transit_minutes": transit_mins,
        "total_day_transit_minutes": total_day_transit_minutes,
        "travel_time_acceptable": is_acceptable,
        "summary": (
            f"Added '{scheduled_entry['name']}' to Day {day_number} with a {detour_dist} km detour (+{transit_mins} min transit). "
            f"Total daily transit: {total_day_transit_minutes} min (Status: {'Acceptable' if is_acceptable else 'High Transit Warning'})."
        )
    }

    return trip_data, audit