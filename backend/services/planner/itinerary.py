
from backend.services.external.location_service import search_location
from backend.services.external.route_service import get_route
from backend.services.external.weather_service import get_weather
from backend.services.external.place_service import get_places
from backend.services.external.hotel_service import get_hotels
from backend.services.planner import traveler_conflicts
from backend.services.planner.transport_planner import (
    build_transport_plan,
)
from backend.services.planner import travel_mode
from backend.services.planner.attraction_ranker import rank_places
from backend.services.planner.preference_matcher import match_preferences
from backend.services.planner.mandatory_scheduler import schedule_mandatory_visits
from backend.services.planner.travel_mode import get_mode_rules
from backend.services.planner.route_attractions import get_route_attractions
from backend.services.planner.budget_engine import get_budget_rules
from backend.services.planner.day_planner import plan_days
from backend.services.planner.trip_optimizer import optimize_trip
from backend.services.planner.trip_summary import build_summary
from backend.services.planner.budget_tracker import calculate_budget
from backend.services.planner.dashboard import build_dashboard
from backend.services.planner.best_time_suggester import (
    suggest_best_days,
    suggest_best_time,
)
from backend.services.planner.traveler_conflicts import (
    detect_traveler_conflicts,
    get_shared_interests,
    get_interest_priority,
)
from backend.services.planner.weather_planner import (
    adjust_schedule_for_weather,
)

from backend.services.storage.trip_store import save_trip

async def build_trip(request):
    if getattr(request, "destinations", None) and len(request.destinations) > 1:
        from backend.services.planner.multi_destination import build_multi_destination_trip
        return await build_multi_destination_trip(request)

    source = request.source
    destination = request.destination
    days = request.days
    travelers = request.travelers
    travel_mode = request.travel_mode
    mandatory_visits = list(request.mandatory_visits or [])

    raw_constraints = getattr(request, "constraints", None)
    constraints_dict = (
        raw_constraints.dict()
        if raw_constraints and hasattr(raw_constraints, "dict")
        else (raw_constraints if isinstance(raw_constraints, dict) else {})
    )
    from backend.services.planner.constraint_engine import (
        validate_constraints,
        filter_avoided_locations,
        evaluate_constraints_satisfaction,
    )
    is_valid_constraints, constraint_errors = validate_constraints(constraints_dict)
    if not is_valid_constraints:
        return {
            "error": "Constraint validation failed",
            "details": constraint_errors,
        }

    # Merge must_visit_locations from constraints into mandatory_visits
    raw_must = constraints_dict.get("must_visit_locations") or constraints_dict.get("must_visit") or []
    if raw_must:
        from backend.models.trip import MandatoryVisit
        for mv in raw_must:
            mv_name = str(mv).strip()
            if mv_name and not any(v.name.lower() == mv_name.lower() for v in mandatory_visits):
                mandatory_visits.append(MandatoryVisit(name=mv_name))

    traveler_profiles = []

    for traveler in travelers:
        profile = traveler.dict()

        profile["budget_rules"] = get_budget_rules(
            traveler.budget
        )

        traveler_profiles.append(profile)


    mode_rules = get_mode_rules(travel_mode)

    mandatory_schedule = schedule_mandatory_visits(
        days,
        [visit.dict() for visit in mandatory_visits],
    )


    source_location = await search_location(source)
    destination_location = await search_location(destination)

    if source_location is None or destination_location is None:
        return {
            "error": "Source or destination not found"
        }
    print("Destination location:")
    print(destination_location)

    places = await get_places(
        float(destination_location["lat"]),
        float(destination_location["lon"]),
    )
    places, excluded_places = filter_avoided_locations(
        places,
        constraints_dict.get("locations_to_avoid")
    )
    print("Raw places after constraint filtering:", len(places))
    route = await get_route(
        float(source_location["lon"]),
        float(source_location["lat"]),
        float(destination_location["lon"]),
        float(destination_location["lat"]),
    )

    route_summary = {
        "distance_km": round(
            route["routes"][0]["distance"] / 1000,
            2,
        ),
        "duration_hours": round(
            route["routes"][0]["duration"] / 3600,
            2,
        ),
    }
    transport_summary = build_transport_plan(
    source,
    destination,
    travel_mode,
    route_summary["distance_km"],
    route_summary["duration_hours"],
)
    

    weather = await get_weather(
        float(destination_location["lat"]),
        float(destination_location["lon"]),
    )

    weather_summary = []

    daily = weather["daily"]

    for i in range(len(daily["time"])):
        weather_summary.append(
            {
                "date": daily["time"][i],
                "max_temp": daily["temperature_2m_max"][i],
                "min_temp": daily["temperature_2m_min"][i],
                "weather_code": daily["weathercode"][i],
            }
        )

    best_time = suggest_best_days(weather_summary)

    

    place_list = []

    for place in places:

        if not place.get("name"):
            continue
        
        place_list.append(
            {
                "name": place["name"],
                "category": place.get("kinds", "")
                .split(",")[0]
                .replace("_", " ")
                .title(),
                "distance_km": round(
                    place.get("dist", 0) / 1000,
                    2,
                ),
                "lat": place.get("point", {}).get("lat"),
                "lon": place.get("point", {}).get("lon"),
            }
        )

    print("Place list:", len(place_list))
    place_list = [
    place
    for place in place_list
    if place["distance_km"] <= 15
    ]
    ranked_places = rank_places(
        place_list,
        [traveler.dict() for traveler in travelers],
    )

    print("Ranked places:", len(ranked_places))
    matched_places = match_preferences(
        ranked_places,
        [traveler.dict() for traveler in travelers]
    )
    traveler_data = [
        traveler.dict()
        for traveler in travelers
    ]

    interest_counts = get_shared_interests(
        traveler_data
    )
    traveler_conflicts = detect_traveler_conflicts(
        [traveler.dict() for traveler in travelers],
        matched_places,
    )

    print("\nTRAVELER CONFLICTS:")

    for conflict in traveler_conflicts:
        print(
            conflict["type"],
            "|",
            conflict["message"],
        )

    print(
        "Matched places:",
        len(matched_places)
    )

    seen = set()

    unique_places = []

    for place in matched_places:
        place["interest_priority"] = get_interest_priority(
            place,
            interest_counts,
        )
        matched_places.sort(
            key=lambda place: (
                place.get("interest_priority", 0),
                place.get("score", 0),
            ),
            reverse=True,
        )
        normalized_name = (
            place["name"]
            .lower()
            .replace(" ", "")
        )

        if normalized_name in seen:
            continue

        seen.add(normalized_name)

        unique_places.append(place)

    matched_places = unique_places

    print(
        "Unique places:",
        len(matched_places)
    )
    print("\nINTEREST DISTRIBUTION:")

    for place in matched_places:
        print(
            place["name"],
            "|",
            place["category"],
            "|",
            place.get("matched_interests", []),
            "| score:",
            place.get("score"),
        )
    day_schedule = optimize_trip(
        matched_places,
        days,
        mandatory_schedule,
        pace=traveler_profiles[0]["pace"],
        constraints=constraints_dict,
    )
    from backend.services.planner.weather_planner import replan_trip_for_weather
    day_schedule, weather_replanning = replan_trip_for_weather(
        day_schedule,
        weather_summary,
        available_places=matched_places,
    )

    from backend.services.planner.opening_hours_scheduler import apply_opening_hours_to_schedule
    day_schedule, opening_hours_notes = apply_opening_hours_to_schedule(
        day_schedule=day_schedule,
        travel_mode=travel_mode,
        available_places=matched_places,
    )
    print("\nWEATHER & OPENING-HOURS-AWARE SCHEDULE:")


    for index, (day, places) in enumerate(day_schedule.items()):
        if index >= len(weather_summary):
            break

        print(
            f"Day {day}:",
            weather_summary[index]["date"],
            "| Weather code:",
            weather_summary[index]["weather_code"],
        )

        for place in places:
            print(
                " -",
                place["name"],
            )
    print(
        "Scheduled attractions:",
        sum(len(day) for day in day_schedule.values())
    )
  
    print("Matched places:", len(matched_places))

    unique_places = {}
    cleaned_places = []

    for place in matched_places:

        name = place["name"].strip().lower()

        if name in unique_places:
            continue

        unique_places[name] = True

        cleaned_places.append(place)

    matched_places = cleaned_places
    print("Unique places before route attractions:", len(matched_places))
    matched_places = await get_route_attractions(
        route,
        matched_places,
        travel_mode,
    )
    for place in matched_places:
        time_suggestion = suggest_best_time(place)

        place["best_time"] = time_suggestion["best_time"]
        place["best_time_reason"] = time_suggestion["reason"]
    print("Route attractions after:", len(matched_places))

    print(
        "First 5 places:",
        [p["name"] for p in matched_places[:5]]
    )
    print("Travel mode:", travel_mode)
    print(type(travel_mode))
    

    try:

        hotels = await get_hotels(
            float(destination_location["lat"]),
            float(destination_location["lon"]),
        )

    except Exception as e:

        print(f"Hotel API Error: {e}")

        hotels = []

    hotel_list = []

    for hotel in hotels:

        if not hotel.get("name"):
            continue

        hotel_list.append(
            {
                "name": hotel["name"],
                "distance_km": round(
                    hotel.get("dist", 0) / 1000,
                    2,
                ),
                "lat": hotel.get("point", {}).get("lat"),
        "lon": hotel.get("point", {}).get("lon"),
            }
        )

    
    
    print(
        "FINAL PLACE SAMPLE:",
        matched_places[:3]
    )

    scheduled_activity_count = sum(
    len(places)
    for places in day_schedule.values()
)

    budget = calculate_budget(
        traveler_profiles,
        days,
        travel_mode,
        hotel_list,
        matched_places,
        scheduled_activity_count=
            scheduled_activity_count,
        )

    
    trip_data = {
        "planner_version": "1.0",
        "is_multi_destination": False,

        "source": source,
        "destination": destination,
        "days": days,
        
        "travelers": traveler_profiles,
        "traveler_conflicts": traveler_conflicts,
        "mandatory_visits": [
            visit.dict()
            for visit in mandatory_visits
        ],
        "destination_location": {
        "lat": float(destination_location["lat"]),
        "lon": float(destination_location["lon"]),
    },
        "mandatory_schedule": mandatory_schedule,

        "travel_mode": travel_mode,

        "travel_mode_rules": mode_rules,

        "route": route_summary,
        "transport": transport_summary,
        
        "weather": weather_summary,

        "best_time": best_time,

        "places": matched_places,

        "hotels": hotel_list,

        "day_schedule": day_schedule,

        "budget": budget,
    }

    constraint_analysis = evaluate_constraints_satisfaction(
        day_schedule,
        budget,
        constraints_dict,
        mandatory_visits=[visit.dict() for visit in mandatory_visits],
    )
    trip_data["constraint_analysis"] = constraint_analysis
    trip_data["constraints"] = constraints_dict
    trip_data["opening_hours_notes"] = opening_hours_notes
    trip_data["weather_replanning"] = weather_replanning


    from backend.services.planner.meal_and_break_engine import attach_meals_and_breaks_to_itinerary
    meals_and_breaks = attach_meals_and_breaks_to_itinerary(
        day_schedule=day_schedule,
        available_places=matched_places,
        travelers=traveler_profiles,
    )
    trip_data["meals_and_breaks"] = meals_and_breaks

    from backend.services.planner.route_attractions import discover_route_attractions
    trip_data["route_attractions"] = await discover_route_attractions(
        route=route,
        destination_places=matched_places,
        travel_mode=travel_mode,
    )



    trip_data["dashboard"] = build_dashboard(
        trip_data
    )
    trip_data["dashboard"]["constraint_analysis"] = constraint_analysis


    trip_data["summary"] = build_summary(
        trip_data
    )


    trip_id = save_trip(
        {
            "trip": trip_data,
            "dashboard": trip_data["dashboard"],
            "summary": trip_data["summary"],
        }
    )


    return {
        "trip_id": trip_id,
        "dashboard": trip_data["dashboard"],
        "summary": trip_data["summary"],
        "trip": trip_data,
    }