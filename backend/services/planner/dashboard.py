def build_dashboard(trip_data):
    return {
        "source": trip_data["source"],
        "destination": trip_data["destination"],
        "days": trip_data["days"],
        "travel_mode": trip_data["travel_mode"],
        "weather": trip_data["weather"][0]["weather_code"],
        "hotel_count": len(trip_data["hotels"]),
        "attraction_count": len(trip_data["places"]),
        "mandatory_count": sum(
            len(v)
            for v in trip_data["mandatory_schedule"].values()
        ),
        "distance": trip_data["transport"]["distance_km"],
        "duration": trip_data["transport"]["road_duration_hours"],
        "budget": trip_data["budget"]["total_budget"],
    }