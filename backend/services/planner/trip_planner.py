from services.external.location_service import search_location
from services.external.route_service import get_route
from services.external.weather_service import get_weather
from services.external.place_service import get_places
from services.ai.itinerary_generator import generate_itinerary
from services.planner.attraction_ranker import rank_places
from services.planner.preference_matcher import match_preferences
from services.planner.mandatory_scheduler import schedule_mandatory_visits
from services.planner.travel_mode import get_mode_rules
from services.planner.route_attractions import get_route_attractions
async def build_trip(request):
    source = request.source
    destination = request.destination
    days = request.days
    travelers = request.travelers
    travel_mode = request.travel_mode
    mode_rules = get_mode_rules(travel_mode)
    mandatory_visits = request.mandatory_visits
    mandatory_schedule = schedule_mandatory_visits(
    days,
    [visit.dict() for visit in mandatory_visits]
)

    # Search locations
    source_location = await search_location(source)
    destination_location = await search_location(destination)

    if source_location is None or destination_location is None:
        return {"error": "Source or destination not found"}

    # Route
    route = await get_route(
        float(source_location["lon"]),
        float(source_location["lat"]),
        float(destination_location["lon"]),
        float(destination_location["lat"])
    )

    # Weather
    weather = await get_weather(
        float(destination_location["lat"]),
        float(destination_location["lon"])
    )
    daily = weather["daily"]

    weather_summary = []

    for i in range(len(daily["time"])):
        weather_summary.append({
            "date": daily["time"][i],
            "max_temp": daily["temperature_2m_max"][i],
            "min_temp": daily["temperature_2m_min"][i],
            "weather_code": daily["weathercode"][i]
        })

    # Nearby places
    places = await get_places(
        float(destination_location["lat"]),
        float(destination_location["lon"])
    )

    # Clean places response
    place_list = []

    for place in places:
        if not place.get("name"):
            continue

        place_list.append({
            "name": place["name"],
            "category": place.get("kinds", "").split(",")[0].replace("_", " ").title(),
            "distance_km": round(place.get("dist", 0) / 1000, 2)
        })
        ranked_places = rank_places(
    place_list,
    [traveler.dict() for traveler in travelers]
)
    matched_places = match_preferences(
    ranked_places,
    [traveler.dict() for traveler in travelers]
)
    place_list = await get_route_attractions(
    route,
    place_list,
    travel_mode
)

    # Combined response
    trip_data= {
        "source": source,
        "destination": destination,
        "days": days,
        "travelers": [traveler.dict() for traveler in travelers],
        "mandatory_visits": [visit.dict() for visit in mandatory_visits],
        "mandatory_schedule": mandatory_schedule,
        "route": {
            "distance_km": round(route["routes"][0]["distance"] / 1000, 2),
            "duration_hours": round(route["routes"][0]["duration"] / 3600, 2)
        },
        "travel_mode": travel_mode,
        "travel_mode_rules": mode_rules,
        "weather": weather_summary,
        "places": matched_places[:10]
        
    }
    itinerary = await generate_itinerary(trip_data)

    return {
        "trip": trip_data,
        "itinerary": itinerary
    }
