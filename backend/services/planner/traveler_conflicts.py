def detect_traveler_conflicts(travelers, places):
    conflicts = []

    if not travelers:
        return conflicts

    # Pace conflict
    paces = {
        traveler.get("pace")
        for traveler in travelers
        if traveler.get("pace")
    }

    if len(paces) > 1:
        conflicts.append({
            "type": "pace",
            "travelers": [
                traveler.get("name")
                for traveler in travelers
            ],
            "message": (
                "Travelers have different preferred travel paces."
            ),
        })

    # Interest conflict
    interests = {}

    for traveler in travelers:
        name = traveler.get("name", "Traveler")
        traveler_interests = traveler.get("interests", [])

        interests[name] = set(
            interest.lower()
            for interest in traveler_interests
        )

    all_interests = set()

    for traveler_interests in interests.values():
        all_interests.update(traveler_interests)

    for interest in all_interests:
        interested = [
            name
            for name, traveler_interests in interests.items()
            if interest in traveler_interests
        ]

        if len(interested) == 1 and len(travelers) > 1:
            conflicts.append({
                "type": "interest",
                "interest": interest,
                "travelers": interested,
                "message": (
                    f"Only {interested[0]} is interested in "
                    f"{interest}."
                ),
            })

    return conflicts
def get_shared_interests(travelers):
    interest_counts = {}

    for traveler in travelers:
        for interest in traveler.get("interests", []):
            interest = interest.lower()

            interest_counts[interest] = (
                interest_counts.get(interest, 0) + 1
            )

    return interest_counts
def get_interest_priority(place, interest_counts):
    interests = place.get("matched_interests", [])

    if not interests:
        return 0

    return max(
        interest_counts.get(
            interest.lower(),
            0
        )
        for interest in interests
    )