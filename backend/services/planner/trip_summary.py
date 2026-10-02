def build_summary(trip):
    day_schedule = trip.get("day_schedule") or {}

    total_activities = sum(
        len(places)
        for places in day_schedule.values()
    )

    return {
        "days": trip["days"],
        "distance": trip["route"]["distance_km"],
        "travel_time": trip["route"]["duration_hours"],
        "hotel_count": len(trip["hotels"]),
        "place_count": len(trip["places"]),
        "scheduled_activities": total_activities,
        "travelers": len(trip.get("travelers", [])),
        "travel_mode": trip.get("travel_mode"),
    }