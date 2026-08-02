INTEREST_MAP = {
    "Beaches": ["Beach"],
    "Food": ["Restaurant", "Cafe", "Market"],
    "Photography": ["Historic", "Cultural", "Viewpoint"],
    "Adventure": ["Adventure", "Waterfall"],
    "Water Sports": ["Beach", "Adventure"],
    "Religion": ["Religion"],
    "History": ["Historic"],
    "Nature": ["Nature", "Waterfall", "Park"]
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

