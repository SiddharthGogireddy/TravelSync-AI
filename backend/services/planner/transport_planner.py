def build_transport_summary(
    source,
    destination,
    travel_mode,
    route,
):
    travel_mode = travel_mode.strip().lower()
    road_distance_km = round(
        route["routes"][0]["distance"] / 1000,
        2,
    )

    road_duration_hours = round(
        route["routes"][0]["duration"] / 3600,
        2,
    )

    mode_info = {
        "car": {
            "label": "Car",
            "description": "Road travel by car",
            "distance_label": "Road Distance",
            "duration_label": "Estimated Driving Time",
            "distance_km": road_distance_km,
            "duration_hours": road_duration_hours,
        },

        "bus": {
            "label": "Bus",
            "description": "Intercity bus travel",
            "distance_label": "Road Distance",
            "duration_label": "Estimated Bus Travel Time",
            "distance_km": road_distance_km,
            "duration_hours": round(
                road_duration_hours * 1.15,
                2,
            ),
        },

        "train": {
            "label": "Train",
            "description": "Rail travel",
            "distance_label": "Estimated Rail Distance",
            "duration_label": "Estimated Train Travel Time",
            "distance_km": round(
                road_distance_km * 0.95,
                2,
            ),
            "duration_hours": round(
                road_duration_hours * 1.10,
                2,
            ),
        },

        "flight": {
            "label": "Flight",
            "description": "Air travel",
            "distance_label": "Estimated Air Distance",
            "duration_label": "Estimated Flight Time",
            "distance_km": round(
                road_distance_km * 0.80,
                2,
            ),
            "duration_hours": round(
                road_duration_hours * 0.18,
                2,
            ),
        },
    }

    selected = mode_info.get(
        travel_mode,
        mode_info["car"],
    )
    print("TRANSPORT MODE:", travel_mode)
    print("TRANSPORT SELECTED:", selected)
    return {
        "mode": travel_mode,
        "label": selected["label"],
        "description": selected["description"],
        "distance_label": selected["distance_label"],
        "duration_label": selected["duration_label"],
        "source": source,
        "destination": destination,
        "distance_km": selected["distance_km"],
        "road_duration_hours": selected["duration_hours"],
    }