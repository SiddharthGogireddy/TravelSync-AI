async def get_route_attractions(
    route,
    destination_places,
    travel_mode
):
    attractions = []

    if travel_mode == "car":
        attractions.extend(destination_places)

    elif travel_mode == "bus":
        attractions.extend(destination_places)

    elif travel_mode == "train":
        attractions.extend(destination_places)

    elif travel_mode == "flight":
        attractions.extend(destination_places)

    return attractions