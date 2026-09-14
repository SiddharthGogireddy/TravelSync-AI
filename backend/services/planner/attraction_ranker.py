INTEREST_MAP = {
    "Beaches": ["Beach"],
    "Food": ["Restaurant", "Cafe", "Market","Foods"],
    "Photography": ["Historic", "Cultural", "Viewpoint"],
    "Adventure": ["Adventure", "Waterfall"],
    "Water Sports": ["Beach", "Adventure"],
    "Religion": ["Religion"],
    "History": ["Historic"],
    "Nature": ["Nature", "Waterfall", "Park"],
    "Culture": [
        "Cultural",
        "Historic",
        "Historic Architecture",
        "Palaces",
    ],
}


def rank_places(places, travelers):
    print("\n=== TRAVELERS RECEIVED BY RANKER ===")
    for traveler in travelers:
        print(
            traveler["name"],
            "→",
            traveler["interests"]
        )
    for place in places:

        score = 0
        matched_interests = []
        matched_travelers = []

        category = place["category"]

        for traveler in travelers:

            traveler_matched = False

            for interest in traveler["interests"]:

                mapped_categories = INTEREST_MAP.get(
                    interest,
                    []
                )

                if category in mapped_categories:

                    score += 5

                    if interest not in matched_interests:
                        matched_interests.append(
                            interest
                        )

                    traveler_matched = True

            if traveler_matched:
                matched_travelers.append(
                    traveler["name"]
                )

        if place["distance_km"] < 5:
            score += 2

        elif place["distance_km"] < 10:
            score += 1

        place["score"] = score

        place["matched_interests"] = (
            matched_interests
        )

        place["matched_travelers"] = (
            matched_travelers
        )

        place["match_count"] = len(
            matched_travelers
        )

    places.sort(
        key=lambda x: (
            -x["score"],
            x["distance_km"],
        )
    )

    return places