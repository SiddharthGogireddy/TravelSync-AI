def build_summary(trip):
    day_schedule = trip.get("day_schedule") or {}

    total_activities = sum(
        len(places)
        for places in day_schedule.values()
    )

    route = trip.get("route") or {}

    return {
        "days": trip.get("days", 1),
        "distance": route.get("distance_km", 0),
        "distance_km": route.get("distance_km", 0),
        "travel_time": route.get("duration_hours", 0),
        "hotel_count": len(trip.get("hotels", [])),
        "place_count": total_activities,
        "scheduled_activities": total_activities,
        "travelers": len(trip.get("travelers", [])),
        "travel_mode": trip.get("travel_mode"),
    }