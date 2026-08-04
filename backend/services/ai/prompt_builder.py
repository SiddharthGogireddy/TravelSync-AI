


def build_prompt(trip_data):
    route = trip_data["route"]
    weather = trip_data["weather"]
    places = trip_data["places"]
    place_text = ""
    travel_mode = trip_data.get("travel_mode", "car")
    mode_rules = trip_data.get("travel_mode_rules")
    traveler_text = ""
    for traveler in trip_data["travelers"]:

        traveler_text += f"""

Traveler:
{traveler['name']}

Budget:
{traveler['budget']}
IMPORTANT:
The itinerary MUST strictly follow the budget rules.

If the budget is Luxury:
- Recommend only 5-star resorts.
- Recommend premium restaurants.
- Recommend private taxis or chauffeur-driven cars.
- Recommend premium experiences.
- Never recommend budget hotels, hostels, cheap restaurants, or affordable options.

If the budget is Medium:
- Recommend 3-4 star hotels.
- Recommend mid-range restaurants.
- Recommend rental cars or taxis.

If the budget is Budget:
- Recommend hostels or budget hotels.
- Recommend buses, trains, or shared transport.
- Recommend affordable restaurants and free attractions.

"""
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
Follow each traveler's budget.

Recommend hotels matching their budget.

Recommend restaurants matching their budget.

Recommend activities matching their budget.

Do not suggest luxury experiences to budget travelers.

If the travel mode is CAR, include attractions while travelling whenever appropriate.
Generate:
1. Morning activities
2. Afternoon activities
3. Evening activities
4. Food recommendations
5. Travel tips
IMPORTANT:
Generate exactly {trip_data["days"]} days.

Do not add extra days.

Do not omit any day.
Rules:

1. Every mandatory visit MUST appear on specified days.
2. Travelers' budgets MUST be respected.
3. Build the remaining itinerary around them.
4. Optimize travel time.
5. Respect traveler preferences.
6. Avoid suggesting attractions that are too far from the route.
7. Weather conditions must be considered when suggesting outdoor activities.
8. Travel mode rules must be followed.
9. Generate a well-structured itinerary with clear headings for each day, including morning, afternoon, and evening activities, food recommendations, and travel tips.
10. Generate exactly {trip_data["days"]} days. Do not add extra days or omit any day.
Return a well-structured itinerary.
"""

    return prompt