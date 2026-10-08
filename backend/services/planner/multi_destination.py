import copy
from typing import List
from backend.services.external.location_service import search_location
from backend.services.external.route_service import get_route
from backend.services.external.weather_service import get_weather
from backend.services.external.place_service import get_places
from backend.services.external.hotel_service import get_hotels
from backend.services.planner.attraction_ranker import rank_places
from backend.services.planner.preference_matcher import match_preferences
from backend.services.planner.travel_mode import get_mode_rules
from backend.services.planner.transport_planner import build_transport_plan
from backend.services.planner.budget_engine import get_budget_rules
from backend.services.planner.budget_tracker import calculate_budget
from backend.services.planner.dashboard import build_dashboard
from backend.services.planner.trip_summary import build_summary
from backend.services.planner.traveler_conflicts import detect_traveler_conflicts
from backend.services.planner.best_time_suggester import suggest_best_days, suggest_best_time
from backend.services.storage.trip_store import save_trip


async def build_multi_destination_trip(request) -> dict:
    """
    Generates a coordinated itinerary across multiple destination stops.
    Example: Hyderabad -> Bengaluru -> Mysuru -> Goa
    Calculates travel between all destinations, schedules attractions per stop,
    and returns a unified trip object fully compatible with existing trip storage.
    """
    source = request.source
    dest_stops = request.destinations
    travelers = request.travelers
    travel_mode = request.travel_mode
    mandatory_visits = request.mandatory_visits or []

    # 1. Traveler profiles
    traveler_profiles = []
    for traveler in travelers:
        profile = traveler.dict()
        profile["budget_rules"] = get_budget_rules(traveler.budget)
        traveler_profiles.append(profile)

    mode_rules = get_mode_rules(travel_mode)

    # 2. Source location
    source_location = await search_location(source)
    if not source_location:
        return {"error": f"Source city '{source}' not found"}

    # 3. Locate each destination stop
    stops_info = []
    total_days = 0
    current_day = 1

    for idx, stop in enumerate(dest_stops):
        stop_name = stop.name.strip()
        stop_days = max(1, int(stop.days))
        total_days += stop_days

        loc = await search_location(stop_name)
        if not loc:
            # Fallback to source location coordinates if lookup fails
            loc = source_location

        start_day = current_day
        end_day = current_day + stop_days - 1
        current_day = end_day + 1

        stops_info.append({
            "stop_index": idx + 1,
            "name": stop_name,
            "days": stop_days,
            "start_day": start_day,
            "end_day": end_day,
            "location": {
                "lat": float(loc["lat"]),
                "lon": float(loc["lon"]),
            },
        })

    # Destination title: e.g. "Bengaluru -> Mysuru -> Goa"
    composite_destination = " -> ".join(
        [s["name"].split(",")[0].strip() for s in stops_info]
    )

    # 4. Calculate travel between consecutive stops (Source -> Stop 1 -> Stop 2 -> ...)
    inter_destination_travel = []
    total_distance_km = 0.0
    total_duration_hours = 0.0

    prev_loc = source_location
    prev_name = source

    for idx, stop in enumerate(stops_info):
        curr_loc = stop["location"]
        curr_name = stop["name"]

        route_res = await get_route(
            float(prev_loc["lon"]),
            float(prev_loc["lat"]),
            float(curr_loc["lon"]),
            float(curr_loc["lat"]),
        )

        leg_distance_km = round(route_res["routes"][0]["distance"] / 1000, 2)
        leg_duration_hours = round(route_res["routes"][0]["duration"] / 3600, 2)

        total_distance_km += leg_distance_km
        total_duration_hours += leg_duration_hours

        inter_destination_travel.append({
            "leg_index": idx + 1,
            "from_location": prev_name,
            "to_location": curr_name,
            "distance_km": leg_distance_km,
            "duration_hours": leg_duration_hours,
            "travel_mode": travel_mode,
            "departure_day": stop["start_day"],
        })

        prev_loc = curr_loc
        prev_name = curr_name

    # 5. Discover attractions and hotels for each destination stop
    all_places = []
    all_hotels = []
    day_schedule = {}
    primary_weather_summary = []

    for stop in stops_info:
        lat = stop["location"]["lat"]
        lon = stop["location"]["lon"]
        stop_name = stop["name"]

        # Weather for this stop
        try:
            weather_data = await get_weather(lat, lon)
            daily = weather_data.get("daily", {})
            times = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            wcodes = daily.get("weathercode", [])
            stop_weather = []
            for i in range(len(times)):
                stop_weather.append({
                    "date": times[i],
                    "max_temp": max_temps[i] if i < len(max_temps) else 30,
                    "min_temp": min_temps[i] if i < len(min_temps) else 20,
                    "weather_code": wcodes[i] if i < len(wcodes) else 0,
                    "destination": stop_name,
                })
            if not primary_weather_summary:
                primary_weather_summary = stop_weather
        except Exception:
            stop_weather = []

        # Places for this stop
        try:
            raw_places = await get_places(lat, lon)
        except Exception:
            raw_places = []

        stop_places = []
        for p in raw_places:
            if not p.get("name"):
                continue
            stop_places.append({
                "name": p["name"],
                "category": p.get("kinds", "").split(",")[0].replace("_", " ").title() or "Sightseeing",
                "distance_km": round(p.get("dist", 0) / 1000, 2),
                "lat": p.get("point", {}).get("lat", lat),
                "lon": p.get("point", {}).get("lon", lon),
                "destination": stop_name,
            })

        # Rank and match places with traveler preferences
        ranked = rank_places(stop_places, [t.dict() for t in travelers])
        matched = match_preferences(ranked, [t.dict() for t in travelers])

        # Dedup places
        seen_names = set()
        clean_matched = []
        for p in matched:
            norm = p["name"].lower().strip()
            if norm not in seen_names:
                seen_names.add(norm)
                # Suggest time
                sugg = suggest_best_time(p)
                p["best_time"] = sugg.get("best_time", "Morning")
                p["best_time_reason"] = sugg.get("reason", "Great morning ambiance")
                clean_matched.append(p)

        all_places.extend(clean_matched)
        stop["attraction_count"] = len(clean_matched)

        # Distribute attractions across this stop's allocated days
        # E.g., 2 to 4 attractions per day
        allocated_days = list(range(stop["start_day"], stop["end_day"] + 1))
        place_idx = 0
        for d in allocated_days:
            # Assign up to 3 attractions per day for this stop
            day_acts = clean_matched[place_idx: place_idx + 3]
            place_idx += 3
            day_schedule[str(d)] = day_acts

        # Hotels for this stop
        try:
            raw_hotels = await get_hotels(lat, lon)
        except Exception:
            raw_hotels = []

        for h in raw_hotels:
            if not h.get("name"):
                continue
            all_hotels.append({
                "name": h["name"],
                "distance_km": round(h.get("dist", 0) / 1000, 2),
                "lat": h.get("point", {}).get("lat", lat),
                "lon": h.get("point", {}).get("lon", lon),
                "destination": stop_name,
            })
        stop["hotel_count"] = len(raw_hotels)

    from backend.services.planner.opening_hours_scheduler import apply_opening_hours_to_schedule
    day_schedule, opening_hours_notes = apply_opening_hours_to_schedule(
        day_schedule=day_schedule,
        travel_mode=travel_mode,
        available_places=all_places,
    )

    # 6. Overall summaries
    route_summary = {

        "distance_km": round(total_distance_km, 2),
        "duration_hours": round(total_duration_hours, 2),
    }

    transport_summary = build_transport_plan(
        source,
        composite_destination,
        travel_mode,
        route_summary["distance_km"],
        route_summary["duration_hours"],
    )

    traveler_conflicts = detect_traveler_conflicts(
        [t.dict() for t in travelers],
        all_places,
    )

    scheduled_activity_count = sum(len(p) for p in day_schedule.values())

    budget = calculate_budget(
        traveler_profiles,
        total_days,
        travel_mode,
        all_hotels,
        all_places,
        scheduled_activity_count=scheduled_activity_count,
    )

    best_time = suggest_best_days(primary_weather_summary) if primary_weather_summary else []

    # 7. Construct complete trip data dictionary
    first_loc = stops_info[0]["location"] if stops_info else {"lat": 0.0, "lon": 0.0}

    trip_data = {
        "planner_version": "1.0",
        "is_multi_destination": True,
        "source": source,
        "destination": composite_destination,
        "days": total_days,
        "destinations": stops_info,
        "inter_destination_travel": inter_destination_travel,
        "travelers": traveler_profiles,
        "traveler_conflicts": traveler_conflicts,
        "mandatory_visits": [v.dict() for v in mandatory_visits],
        "destination_location": first_loc,
        "mandatory_schedule": {},
        "travel_mode": travel_mode,
        "travel_mode_rules": mode_rules,
        "route": route_summary,
        "transport": transport_summary,
        "weather": primary_weather_summary,
        "best_time": best_time,
        "places": all_places,
        "hotels": all_hotels,
        "day_schedule": day_schedule,
        "budget": budget,
        "opening_hours_notes": opening_hours_notes,
    }

    from backend.services.planner.meal_and_break_engine import attach_meals_and_breaks_to_itinerary
    trip_data["meals_and_breaks"] = attach_meals_and_breaks_to_itinerary(
        day_schedule=day_schedule,
        available_places=all_places,
        travelers=traveler_profiles,
    )



    # 8. Dashboard and Summary
    trip_data["dashboard"] = build_dashboard(trip_data)
    # Enhance dashboard with multi-destination info
    trip_data["dashboard"]["is_multi_destination"] = True
    trip_data["dashboard"]["destinations_count"] = len(stops_info)
    trip_data["dashboard"]["destinations_summary"] = [
        {"name": s["name"], "days": s["days"], "start_day": s["start_day"], "end_day": s["end_day"]}
        for s in stops_info
    ]

    trip_data["summary"] = build_summary(trip_data)
    trip_data["summary"]["is_multi_destination"] = True
    trip_data["summary"]["destinations_count"] = len(stops_info)

    # 9. Save trip
    trip_id = save_trip({
        "trip": trip_data,
        "dashboard": trip_data["dashboard"],
        "summary": trip_data["summary"],
    })

    return {
        "trip_id": trip_id,
        "dashboard": trip_data["dashboard"],
        "summary": trip_data["summary"],
        "trip": trip_data,
    }
