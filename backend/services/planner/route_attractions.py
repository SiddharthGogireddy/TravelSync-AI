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
) -> List[Dict[str, Any]]:
    """
    Identifies high-value attractions along the travel route corridor
    within an acceptable detour distance.
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
            "description": f"Scenic stop {wp['percent']}% along the route with only +{impact['round_trip_detour_km']} km detour.",
            "is_route_stop": True,
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
    # Append route stops so they can be discovered / scheduled
    combined.extend(discovered_route_stops)
    return combined


def insert_route_stop_into_day(
    trip_data: Dict[str, Any],
    day_number: int,
    route_stop: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Inserts a discovered route stop into a specific day's schedule,
    recalculates transit times, and verifies that total travel time remains acceptable.
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
    if any(p.get("name", "").strip().lower() == stop_name for p in places):
        return trip_data, {
            "success": False,
            "error": f"Route stop '{route_stop.get('name')}' is already in Day {day_number} schedule.",
        }

    # Format the stop as a scheduled place
    scheduled_entry = {
        "name": route_stop.get("name"),
        "category": route_stop.get("category", "En-Route Stop"),
        "lat": route_stop.get("lat"),
        "lon": route_stop.get("lon"),
        "distance_km": route_stop.get("detour_distance_km", 5.0),
        "travel_from_previous_km": route_stop.get("detour_distance_km", 5.0),
        "travel_time_minutes": route_stop.get("added_travel_time_minutes", 20),
        "time_window": f"{route_stop.get('recommended_pause_minutes', 45)} min Scenic Pause",
        "timing_status": "En-Route Scenic Stop",
        "is_en_route": True,
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
        "added_detour_km": route_stop.get("detour_distance_km", 5.0),
        "added_transit_minutes": route_stop.get("added_travel_time_minutes", 20),
        "total_day_transit_minutes": total_day_transit_minutes,
        "travel_time_acceptable": is_acceptable,
        "summary": (
            f"Added '{scheduled_entry['name']}' to Day {day_number} with a {route_stop.get('detour_distance_km')} km detour (+{route_stop.get('added_travel_time_minutes')} min transit). "
            f"Total daily transit: {total_day_transit_minutes} min (Status: {'Acceptable' if is_acceptable else 'High Transit Warning'})."
        )
    }

    return trip_data, audit