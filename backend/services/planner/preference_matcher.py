INTEREST_MAP = {
    "Beaches": [
        "Beach",
        "Waterfall",
        "Fountains"
    ],

    "Food": [
        "Restaurant",
        "Cafe",
        "Market"
    ],
    "Culture": [
        "Cultural",
        "Historic",
        "Historic Architecture",
        "Palaces"
    ],
    "Photography": [
        "Historic",
        "Historic Architecture",
        "Cultural",
        "Viewpoint",
        "Palaces"
    ],

    "Adventure": [
        "Adventure",
        "Waterfall"
    ],

    "Water Sports": [
        "Beach",
        "Waterfall",
        "Fountains"
    ],

    "Religion": [
        "Religion"
    ],

    "History": [
        "Historic",
        "Historic Architecture",
        "Palaces",
        "Fortifications"
    ],

    "Nature": [
        "Nature",
        "Waterfall",
        "Park"
    ]
}


def match_preferences(places, travelers):

    matches = []

    for place in places:

        satisfied = []

        for traveler in travelers:

            for interest in traveler["interests"]:

                if place["category"] in INTEREST_MAP.get(interest, []):

                    satisfied.append(traveler["name"])

                    break

        place["matched_travelers"] = satisfied
        place["match_count"] = len(satisfied)

        matches.append(place)
        matches.sort(
            key=lambda x: (
            -x["match_count"],
            -x["score"]
            )
        )
    return matches

