INTEREST_MAP = {
    "Beaches": [
        "Beach",
        "Waterfall",
        "Fountains"
    ],

    "Food": [
        "Restaurant",
        "Cafe",
        "Market",
        "Foods"
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
        matched_interests = []

        for traveler in travelers:

            traveler_matched = False

            for interest in traveler["interests"]:

                if place["category"] in INTEREST_MAP.get(interest, []):

                    if traveler["name"] not in satisfied:
                        satisfied.append(traveler["name"])

                    if interest not in matched_interests:
                        matched_interests.append(interest)

                    traveler_matched = True

            # No break here because we want to collect all matching interests

        place["matched_travelers"] = satisfied
        place["match_count"] = len(satisfied)
        place["matched_interests"] = matched_interests

        matches.append(place)

    matches.sort(
        key=lambda x: (
            -x["match_count"],
            -x["score"]
        )
    )

    return matches
