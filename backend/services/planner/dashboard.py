def build_dashboard(trip_data):
    day_schedule = trip_data.get("day_schedule") or {}
    total_activities = sum(len(places) for places in day_schedule.values())
    days_count = max(1, trip_data.get("days", 1))
    activities_per_day = round(total_activities / days_count, 1)

    budget = trip_data.get("budget", {})
    categories = budget.get("categories", {})

    weather_list = trip_data.get("weather", [])
    weather_code = weather_list[0].get("weather_code", "Pleasant") if weather_list else "Pleasant"

    transport = trip_data.get("transport", {})
    route = trip_data.get("route", {})
    distance = transport.get("distance_km") if transport.get("distance_km") is not None else route.get("distance_km", 0)
    duration = transport.get("duration_hours") if transport.get("duration_hours") is not None else route.get("duration_hours", 0)

    mandatory_sched = trip_data.get("mandatory_schedule") or {}
    mandatory_count = sum(len(v) for v in mandatory_sched.values()) if isinstance(mandatory_sched, dict) else 0

    return {
        "source": trip_data.get("source", ""),
        "destination": trip_data.get("destination", ""),
        "days": days_count,
        "travel_mode": trip_data.get("travel_mode", "car"),
        "weather": weather_code,
        "hotel_count": len(trip_data.get("hotels", [])),
        "attraction_count": total_activities,
        "candidate_attractions_count": len(trip_data.get("places", [])),
        "mandatory_count": mandatory_count,
        "total_activities": total_activities,
        "activities_per_day": activities_per_day,
        "distance": distance,
        "duration": duration,
        "budget": budget.get("total_budget", 0),
        "estimated_cost": budget.get("estimated_cost", 0),
        "remaining": budget.get("remaining", 0),
        "budget_status": budget.get("status", "Near Budget"),
        "hotel_cost": categories.get("hotel", 0),
        "food_cost": categories.get("food", 0),
        "transport_cost": categories.get("transport", 0),
        "activity_cost": categories.get("activities", 0),
        "emergency_cost": categories.get("emergency", 0),
        "average_per_day": budget.get("average_per_day", 0),
        "average_per_person": budget.get("average_per_person", 0),
    }