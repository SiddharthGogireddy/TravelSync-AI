def build_summary(trip):
    return {
        "days": trip["days"],
        "distance": trip["route"]["distance_km"],
        "travel_time": trip["route"]["duration_hours"],
        "hotel_count": len(trip["hotels"]),
        "place_count": len(trip["places"])
    }