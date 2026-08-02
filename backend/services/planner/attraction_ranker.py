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


def rank_places(places, travelers):

    for place in places:

        score = 0

        category = place["category"]

        for traveler in travelers:

            for interest in traveler["interests"]:

                mapped_categories = INTEREST_MAP.get(interest, [])

                if category in mapped_categories:
                    score += 5

        if place["distance_km"] < 5:
            score += 2

        elif place["distance_km"] < 10:
            score += 1

        place["score"] = score

    return places

def rank_places(places, travelers):

    for place in places:

        score = 0

        category = place["category"]

        for traveler in travelers:

            for interest in traveler["interests"]:

                mapped_categories = INTEREST_MAP.get(interest, [])

                if category in mapped_categories:
                    score += 5

        if place["distance_km"] < 5:
            score += 2

        elif place["distance_km"] < 10:
            score += 1

        place["score"] = score

    places.sort(
        key=lambda x: (-x["score"], x["distance_km"])
    )

    return places