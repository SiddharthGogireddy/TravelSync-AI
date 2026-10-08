INTEREST_MAP = {
    "Beaches": ["Beach", "Coast", "Beaches", "Seaside", "Shore", "Water Sports", "Resort"],
    "Food": ["Restaurant", "Cafe", "Market", "Foods", "Food", "Fast Food", "Dining", "Bakery", "Pub", "Bar"],
    "History": ["Historic", "History", "Monument", "Fort", "Fortifications", "Archaeology", "Museum", "Castle", "Ruins", "Historic Architecture", "Palaces"],
    "Culture": ["Cultural", "Culture", "Historic", "Historic Architecture", "Palaces", "Museum", "Theatre", "Art", "Gallery", "Memorial", "Heritage"],
    "Nature": ["Nature", "Waterfall", "Park", "Gardens", "Lake", "Forest", "Mountain", "Reserve", "Wildlife", "Viewpoint", "Scenic", "Water"],
    "Adventure": ["Adventure", "Waterfall", "Hiking", "Trekking", "Climbing", "Theme Park", "Amusement", "Sports", "Water"],
    "Shopping": ["Shopping", "Market", "Mall", "Bazaar", "Supermarket", "Commercial", "Crafts"],
    "Religion": ["Religion", "Temple", "Church", "Mosque", "Chapel", "Cathedral", "Shrine", "Monastery", "Religious", "Spiritual"],
    "Nightlife": ["Nightlife", "Pubs", "Pub", "Bar", "Bars", "Nightclub", "Club", "Lounge", "Disco", "Casino", "Entertainment"],
    "Photography": ["Historic", "Cultural", "Viewpoint", "Scenic"],
    "Water Sports": ["Beach", "Adventure", "Water"],
}


def _get_mapped_categories(interest: str) -> list:
    cleaned = interest.strip().lower()
    for key, mapped in INTEREST_MAP.items():
        if key.lower() == cleaned:
            return mapped
    return [interest.title()]


def rank_places(places, travelers):
    for place in places:
        score = 0
        matched_interests = []
        matched_travelers = []
        matched_traveler_preferences = []

        category = place.get("category", "")
        category_lower = category.lower()

        for traveler in travelers:
            traveler_name = traveler.get("name", "Traveler")
            traveler_matched = False
            traveler_matched_interests = []

            for interest in traveler.get("interests", []):
                mapped_categories = _get_mapped_categories(interest)

                # Match if category equals or contains any mapped tag, or vice versa
                is_match = any(
                    cat.lower() == category_lower or cat.lower() in category_lower or category_lower in cat.lower()
                    for cat in mapped_categories
                )

                if is_match:
                    score += 5
                    if interest not in matched_interests:
                        matched_interests.append(interest)
                    traveler_matched = True
                    traveler_matched_interests.append(interest)

            if traveler_matched:
                matched_travelers.append(traveler_name)
                matched_traveler_preferences.append({
                    "traveler": traveler_name,
                    "interests": traveler_matched_interests,
                })


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

        place["matched_traveler_preferences"] = matched_traveler_preferences

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