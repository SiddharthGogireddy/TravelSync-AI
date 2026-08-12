from backend.services.external.location_service import search_location
from backend.services.external.route_service import get_route
from backend.services.external.weather_service import get_weather
from backend.services.external.place_service import get_places
from backend.services.external.hotel_service import get_hotels

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
from backend.services.planner.best_time_suggester import suggest_best_days

from backend.services.storage.trip_store import save_trip

def optimize_trip(
    places,
    days,
    mandatory_schedule=None
):

    if mandatory_schedule is None:
        mandatory_schedule = {}

    MAX_PER_DAY = min(
    6,
    max(
        3,
        (len(places) + days - 1) // days
    )
    )

    MAX_CLUSTER_DISTANCE = 5  # km
async def build_trip(request):
    source = request.source
    destination = request.destination
    days = request.days
    travelers = request.travelers
    travel_mode = request.travel_mode
    mandatory_visits = request.mandatory_visits

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


    places = await get_places(
        float(destination_location["lat"]),
        float(destination_location["lon"]),
    )

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

    ranked_places = rank_places(
        place_list,
        [traveler.dict() for traveler in travelers],
    )

    matched_places = match_preferences(
        ranked_places,
        [traveler.dict() for traveler in travelers],
    )


    matched_places = await get_route_attractions(
    route,
    matched_places,
    travel_mode,
)

    day_schedule = optimize_trip(
    matched_places,
    days,
    mandatory_schedule,
)

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
            }
        )

  

    budget = calculate_budget(
        traveler_profiles,
        days,
        travel_mode,
        hotel_list,
        matched_places,
    )


    trip_data = {
        "planner_version": "1.0",

        "source": source,
        "destination": destination,
        "days": days,

        "travelers": traveler_profiles,

        "mandatory_visits": [
            visit.dict()
            for visit in mandatory_visits
        ],

        "mandatory_schedule": mandatory_schedule,

        "travel_mode": travel_mode,

        "travel_mode_rules": mode_rules,

        "route": route_summary,

        "weather": weather_summary,

        "best_time": best_time,

        "places": matched_places,

        "hotels": hotel_list,

        "day_schedule": day_schedule,

        "budget": budget,
    }


    trip_data["dashboard"] = build_dashboard(
        trip_data
    )

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