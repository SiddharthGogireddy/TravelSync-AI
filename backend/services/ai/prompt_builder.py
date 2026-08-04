def build_prompt(trip_data):
    route = trip_data["route"]
    weather = trip_data["weather"]
    places = trip_data["places"]

    hotels = trip_data.get("hotels", [])
    restaurants = trip_data.get("restaurants", [])
    day_schedule = trip_data.get("day_schedule", {})
    mandatory_schedule = trip_data.get("mandatory_schedule", {})

    travel_mode = trip_data.get("travel_mode", "car")
    mode_rules = trip_data.get("travel_mode_rules", {})

    hotel_names = ", ".join(
        hotel["name"]
        for hotel in hotels[:10]
    )
    hotel_list = []

    for hotel in hotels:
        if not hotel.get("name"):
            continue

        hotel_list.append({
            "name": hotel["name"],
            "distance_km": round(hotel["distance"] / 1000, 2)
        })

    restaurant_names = ", ".join(
        restaurant["name"]
        for restaurant in restaurants[:10]
    )

    weather_text = ""

    for day in weather[:trip_data["days"]]:
        weather_text += (
            f"{day['date']} : "
            f"{day['min_temp']}°C - "
            f"{day['max_temp']}°C "
            f"(Code {day['weather_code']})\n"
        )

    traveler_text = ""

    for traveler in trip_data["travelers"]:
        traveler_text += f"""
Traveler: {traveler['name']}
Budget: {traveler['budget']}
Interests: {", ".join(traveler['interests'])}
Travel Pace: {traveler['pace']}
"""

    place_text = ""

    for place in places:
        place_text += f"""
Name: {place["name"]}
Category: {place["category"]}
Recommended For: {", ".join(place["matched_travelers"])}
Satisfies: {place["match_count"]} traveler(s)

"""

    schedule_text = ""

    for day, day_places in day_schedule.items():

        schedule_text += f"\nDay {day}\n"

        for place in day_places:
            schedule_text += f"- {place['name']}\n"

    mandatory_text = ""

    for day, visits in mandatory_schedule.items():

        mandatory_text += f"""
Day {day}
Mandatory Visits:
{", ".join(visits)}

"""

    mode_instruction = ""

    if mode_rules.get("scenic"):
        mode_instruction += "- Suggest scenic stops while travelling.\n"

    if mode_rules.get("route_stops"):
        mode_instruction += "- Include useful rest stops on the journey.\n"

    if mode_rules.get("station"):
        mode_instruction += "- Suggest attractions near railway stations.\n"

    if mode_rules.get("bus_stop"):
        mode_instruction += "- Suggest attractions near major bus terminals.\n"

    if mode_rules.get("airport"):
        mode_instruction += "- Suggest airport transfers and nearby attractions.\n"

    prompt = f"""
You are an expert travel planner.

Create a HIGH QUALITY travel itinerary.

Trip Details

Source:
{trip_data["source"]}

Destination:
{trip_data["destination"]}

Duration:
{trip_data["days"]} days

Travel Mode:
{travel_mode.upper()}

Distance:
{route["distance_km"]} km

Estimated Travel Time:
{route["duration_hours"]} hours

Weather Forecast:
{weather_text}

Nearby Hotels:
{hotel_names}

Nearby Restaurants:
{restaurant_names}

Travelers:
{traveler_text}

Recommended Attractions:
{place_text}

Suggested Attractions Per Day:
{schedule_text}

Mandatory Schedule:
{mandatory_text}

Travel Mode Instructions:
{mode_instruction}

Budget Rules

Luxury:
- Recommend only luxury hotels.
- Recommend premium restaurants.
- Recommend premium experiences.
- Recommend private transport.

Medium:
- Recommend 3-4 star hotels.
- Recommend mid-range restaurants.
- Recommend rental cars or taxis.

Budget:
- Recommend hostels or budget hotels.
- Recommend affordable restaurants.
- Recommend buses or trains where applicable.

Rules

1. Generate EXACTLY {trip_data["days"]} days.
2. Do not generate extra days.
3. Every mandatory visit must appear on the assigned day.
4. Use the suggested attractions naturally.
5. Do not repeat attractions.
6. Balance attractions across days.
7. Respect weather.
8. Respect travel mode.
9. Respect every traveler's budget.
10. Recommend hotels from the Nearby Hotels list.
11. Recommend restaurants from the Nearby Restaurants list.
12. Keep travel efficient.
13. Avoid unnecessary backtracking.

For EACH day include:

- Morning
- Afternoon
- Evening
- Recommended Hotel
- Food Recommendations
- Travel Tips
-Only recommend hotels from the Nearby Hotels list.

-If the list is empty, say:
"No nearby hotel information available."
-Use ONLY restaurants from the Nearby Restaurants list.
-Higher scored attractions are more important.

Prioritize higher scored attractions.
-Generate exactly {trip_data["days"]} travel days.
-Choose hotels ONLY from the Nearby Hotels list.

If no hotel satisfies the budget, mention that no suitable hotel was found.

Do not invent hotels.
Do not automatically include the return journey unless explicitly requested.
Only use low scored attractions if time remains.
Do not invent restaurant names.
Return a beautifully formatted itinerary using Markdown headings.
"""

    return prompt