TRAVEL_MODE_RULES = {

    "car": {
        "route_stops": True,
        "airport": False,
        "station": False,
        "bus_stop": False,
        "scenic": True
    },

    "bus": {
        "route_stops": True,
        "airport": False,
        "station": False,
        "bus_stop": True,
        "scenic": False
    },

    "train": {
        "route_stops": False,
        "airport": False,
        "station": True,
        "bus_stop": False,
        "scenic": False
    },

    "flight": {
        "route_stops": False,
        "airport": True,
        "station": False,
        "bus_stop": False,
        "scenic": False
    }

}
def get_mode_rules(mode):

    return TRAVEL_MODE_RULES.get(
        mode,
        TRAVEL_MODE_RULES["car"]
    )