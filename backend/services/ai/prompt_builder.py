


def build_prompt(trip_data):
    route = trip_data["route"]
    weather = trip_data["weather"]
    places = trip_data["places"]
    place_text = ""
    travel_mode = trip_data.get("travel_mode", "car")
    mode_rules = trip_data.get("travel_mode_rules")
    mode_instruction = ""
    if mode_rules["scenic"]:
        mode_instruction += (
        "- Suggest scenic stops while travelling.\n"
    )

    if mode_rules["station"]:
        mode_instruction += (
        "- Suggest attractions near railway stations.\n"
    )

    if mode_rules["bus_stop"]:
        mode_instruction += (
        "- Suggest attractions near major bus terminals.\n"
    )

    if mode_rules["airport"]:
        mode_instruction += (
        "- Suggest airport transfer options and nearby attractions.\n"
    )
    for place in places:

        place_text += f"""
    Name: {place["name"]}
    Category: {place["category"]}
    Recommended For: {", ".join(place["matched_travelers"])}
    Satisfies: {place["match_count"]} traveler(s)

    """
    mandatory_text = ""

    for day, visits in trip_data["mandatory_schedule"].items():

        mandatory_text += f"""
    Day {day}

    Mandatory Visits:

    {", ".join(visits)}

"""
    
    prompt = f"""
You are an expert travel planner.

Create a detailed travel itinerary.
Travel Mode: {travel_mode.upper()}
Special Instructions:
{mode_instruction}
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

Recommended Attractions:
{place_text}

Mandatory Schedule:

{mandatory_text}
Travel Mode: {travel_mode.upper()}
Use the recommended attractions naturally across the itinerary.

Do not place every attraction on the same day.

Balance sightseeing across all travel days.

Avoid repeating attractions.

If the travel mode is CAR, include attractions while travelling whenever appropriate.
Generate:
1. Morning activities
2. Afternoon activities
3. Evening activities
4. Food recommendations
5. Travel tips
Rules:

1. Every mandatory visit MUST appear.
2. Do not remove mandatory visits.
3. Build the remaining itinerary around them.
4. Optimize travel time.
5. Respect traveler preferences.
Return a well-structured itinerary.
"""

    return prompt