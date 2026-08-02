from backend.routes.place import places


def build_prompt(trip_data):
    route = trip_data["route"]
    weather = trip_data["weather"]
    places = trip_data["places"]
    place_text = ""

    for place in places:

        place_text += f"""
    Name: {place["name"]}
    Category: {place["category"]}
    Recommended For: {", ".join(place["matched_travelers"])}
    Satisfies: {place["match_count"]} traveler(s)

    """
    
    prompt = f"""
You are an expert travel planner.

Create a detailed travel itinerary.

Source:
{trip_data["source"]}

Destination:
{trip_data["destination"]}

Travel Distance:
{route["distance_km"]} km

Estimated Travel Time:
{route["duration_hours"]} hours

Weather:
{weather}

Nearby Attractions:
{place_text}

Generate:
1. Morning activities
2. Afternoon activities
3. Evening activities
4. Food recommendations
5. Travel tips

Return a well-structured itinerary.
"""

    return prompt