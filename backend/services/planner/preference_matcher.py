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


def match_preferences(places, travelers):
    matches = []

    for place in places:
        satisfied = []
        matched_interests = []
        matched_traveler_preferences = []
        category = place.get("category", "")
        category_lower = category.lower()

        for traveler in travelers:
            traveler_name = traveler.get("name", "Traveler")
            traveler_matched = False
            traveler_matched_interests = []

            for interest in traveler.get("interests", []):
                mapped_categories = _get_mapped_categories(interest)

                is_match = any(
                    cat.lower() == category_lower or cat.lower() in category_lower or category_lower in cat.lower()
                    for cat in mapped_categories
                )

                if is_match:
                    if traveler_name not in satisfied:
                        satisfied.append(traveler_name)

                    if interest not in matched_interests:
                        matched_interests.append(interest)

                    traveler_matched = True
                    traveler_matched_interests.append(interest)

            if traveler_matched:
                matched_traveler_preferences.append({
                    "traveler": traveler_name,
                    "interests": traveler_matched_interests,
                })

        place["matched_travelers"] = satisfied
        place["match_count"] = len(satisfied)
        place["matched_interests"] = matched_interests
        place["matched_traveler_preferences"] = matched_traveler_preferences

        matches.append(place)

    matches.sort(
        key=lambda x: (
            -x["match_count"],
            -x.get("score", 0),
        )
    )

    return matches

