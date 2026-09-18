TRANSPORT_HUBS = {
    "airport": {
        "Hyderabad, Telangana, India": "Rajiv Gandhi International Airport",
        "Bengaluru, Karnataka, India": "Kempegowda International Airport",
        "Mumbai, Maharashtra, India": "Chhatrapati Shivaji Maharaj International Airport",
        "Delhi, India": "Indira Gandhi International Airport",
        "Chennai, Tamil Nadu, India": "Chennai International Airport",
    },

    "railway": {
        "Hyderabad, Telangana, India": "Hyderabad Deccan Railway Station",
        "Bengaluru, Karnataka, India": "KSR Bengaluru City Junction",
        "Mumbai, Maharashtra, India": "Mumbai Central Railway Station",
        "Delhi, India": "New Delhi Railway Station",
        "Chennai, Tamil Nadu, India": "Chennai Central Railway Station",
    },

    "bus": {
        "Hyderabad, Telangana, India": "Mahatma Gandhi Bus Station",
        "Bengaluru, Karnataka, India": "Kempegowda Bus Station",
        "Mumbai, Maharashtra, India": "Mumbai Central Bus Station",
        "Delhi, India": "Kashmere Gate ISBT",
        "Chennai, Tamil Nadu, India": "Chennai Mofussil Bus Terminus",
    },
}
def get_transport_hub(location, hub_type):
    return TRANSPORT_HUBS.get(hub_type, {}).get(
        location,
        f"{hub_type.title()} Station"
    )
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
        origin_station = get_transport_hub(
            source,
            "bus",
        )

        destination_station = get_transport_hub(
            destination,
            "bus",
        )
        legs = [
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer to Bus Station",
                "from": source,
                "to": origin_station,
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
                "from": origin_station,
                "to": destination_station,
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
                "from": destination_station,
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
        origin_station = get_transport_hub(
            source,
            "railway",
        )

        destination_station = get_transport_hub(
            destination,
            "railway",
        )
        legs = [
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer to Railway Station",
                "from": source,
                "to": origin_station,
                "distance_km": round(
                    road_distance_km * 0.04,
                    2,
                ),
                "duration_hours": 0.5,
            },
            {
                "type": "main",
                "mode": "train",
                "label": "Train Journey",
                "from": origin_station,
                "to": destination_station,
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
                "from": destination_station,
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
        origin_airport = get_transport_hub(
            source,
            "airport",
        )

        destination_airport = get_transport_hub(
            destination,
            "airport",
        )
        legs = [
            {
                "type": "road",
                "mode": "local_transfer",
                "label": "Transfer to Airport",
                "from": source,
                "to": origin_airport,
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
                "from": origin_airport,
                "to": origin_airport,
                "distance_km": 0,
                "duration_hours": 2.0,
            },
            {
                "type": "main",
                "mode": "flight",
                "label": "Flight",
                "from": origin_airport,
                "to": destination_airport,
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
                "from": destination_airport,
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