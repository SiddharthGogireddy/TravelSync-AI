def build_transport_plan(
    source,
    destination,
    travel_mode,
    road_distance_km,
    road_duration_hours,
):
    travel_mode = travel_mode.strip().lower()

    modes = {
        "car": {
            "label": "Car",
            "description": "Direct road travel by car",
        },
        "bus": {
            "label": "Bus",
            "description": "Road travel with intercity bus service",
        },
        "train": {
            "label": "Train",
            "description": "Road transfer to railway station followed by rail travel",
        },
        "flight": {
            "label": "Flight",
            "description": "Road transfer to airport followed by air travel",
        },
    }

    selected = modes.get(
        travel_mode,
        modes["car"],
    )

    # -------------------------------------------------
    # CAR
    # -------------------------------------------------

    if travel_mode == "car":

        legs = [
            {
                "type": "road",
                "mode": "car",
                "label": "Drive",
                "from": source,
                "to": destination,
                "distance_km": round(
                    road_distance_km,
                    2,
                ),
                "duration_hours": round(
                    road_duration_hours,
                    2,
                ),
            }
        ]

        total_distance = road_distance_km
        total_duration = road_duration_hours

    # -------------------------------------------------
    # BUS
    # -------------------------------------------------

    elif travel_mode == "bus":

        bus_duration = road_duration_hours * 1.15

        legs = [
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer to Bus Station",
                "from": source,
                "to": "Bus Station",
                "distance_km": round(
                    road_distance_km * 0.03,
                    2,
                ),
                "duration_hours": 0.25,
            },
            {
                "type": "main",
                "mode": "bus",
                "label": "Intercity Bus",
                "from": "Bus Station",
                "to": "Destination Bus Station",
                "distance_km": round(
                    road_distance_km * 0.94,
                    2,
                ),
                "duration_hours": round(
                    bus_duration,
                    2,
                ),
            },
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer from Bus Station",
                "from": "Destination Bus Station",
                "to": destination,
                "distance_km": round(
                    road_distance_km * 0.03,
                    2,
                ),
                "duration_hours": 0.25,
            },
        ]

        total_distance = sum(
            leg["distance_km"]
            for leg in legs
        )

        total_duration = sum(
            leg["duration_hours"]
            for leg in legs
        )

    # -------------------------------------------------
    # TRAIN
    # -------------------------------------------------

    elif travel_mode == "train":

        train_duration = road_duration_hours * 1.10

        legs = [
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer to Railway Station",
                "from": source,
                "to": "Railway Station",
                "distance_km": round(
                    road_distance_km * 0.03,
                    2,
                ),
                "duration_hours": 0.25,
            },
            {
                "type": "main",
                "mode": "train",
                "label": "Train Journey",
                "from": "Railway Station",
                "to": "Destination Railway Station",
                "distance_km": round(
                    road_distance_km * 0.95,
                    2,
                ),
                "duration_hours": round(
                    train_duration,
                    2,
                ),
            },
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer from Railway Station",
                "from": "Destination Railway Station",
                "to": destination,
                "distance_km": round(
                    road_distance_km * 0.03,
                    2,
                ),
                "duration_hours": 0.25,
            },
        ]

        total_distance = sum(
            leg["distance_km"]
            for leg in legs
        )

        total_duration = sum(
            leg["duration_hours"]
            for leg in legs
        )

    # -------------------------------------------------
    # FLIGHT
    # -------------------------------------------------

    elif travel_mode == "flight":

        flight_distance = road_distance_km * 0.80
        flight_duration = road_duration_hours * 0.18

        legs = [
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer to Airport",
                "from": source,
                "to": "Airport",
                "distance_km": round(
                    road_distance_km * 0.04,
                    2,
                ),
                "duration_hours": 0.5,
            },
            {
                "type": "airport",
                "mode": "check_in",
                "label": "Airport Check-in",
                "from": "Airport",
                "to": "Airport",
                "distance_km": 0,
                "duration_hours": 2.0,
            },
            {
                "type": "main",
                "mode": "flight",
                "label": "Flight",
                "from": "Origin Airport",
                "to": "Destination Airport",
                "distance_km": round(
                    flight_distance,
                    2,
                ),
                "duration_hours": round(
                    flight_duration,
                    2,
                ),
            },
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer from Airport",
                "from": "Destination Airport",
                "to": destination,
                "distance_km": round(
                    road_distance_km * 0.04,
                    2,
                ),
                "duration_hours": 0.5,
            },
        ]

        total_distance = sum(
            leg["distance_km"]
            for leg in legs
        )

        total_duration = sum(
            leg["duration_hours"]
            for leg in legs
        )

    else:

        raise ValueError(
            f"Unsupported travel mode: {travel_mode}"
        )

    return {
        "label": selected["label"],
        "description": selected["description"],
        "source": source,
        "destination": destination,
        "travel_mode": travel_mode,
        "legs": legs,
        "distance_km": round(
            total_distance,
            2,
        ),
        "duration_hours": round(
            total_duration,
            2,
        ),
    }