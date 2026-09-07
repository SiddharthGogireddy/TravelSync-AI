def build_transport_summary(
    source,
    destination,
    travel_mode,
    route,
):
    distance_km = round(
        route["routes"][0]["distance"] / 1000,
        2,
    )

    duration_hours = round(
        route["routes"][0]["duration"] / 3600,
        2,
    )

    mode_info = {
        "car": {
            "label": "Car",
            "description": "Road travel by car",
        },
        "bus": {
            "label": "Bus",
            "description": "Intercity bus travel",
        },
        "train": {
            "label": "Train",
            "description": "Rail travel",
        },
        "flight": {
            "label": "Flight",
            "description": "Air travel",
        },
    }

    selected = mode_info.get(
        travel_mode,
        mode_info["car"],
    )

    return {
        "mode": travel_mode,
        "label": selected["label"],
        "description": selected["description"],
        "source": source,
        "destination": destination,
        "distance_km": distance_km,
        "road_duration_hours": duration_hours,
    }