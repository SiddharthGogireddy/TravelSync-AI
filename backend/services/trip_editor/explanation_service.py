from backend.services.gemini_service import generate


def explain_attraction(place: dict, trip: dict) -> str:
    prompt = f"""
You are an explanation assistant for TravelSync AI.

Explain why this attraction was selected for the user's itinerary.

Use ONLY the information provided below.
Do not invent facts.
Do not change or calculate scores.
Keep the explanation concise and easy to understand.
Return valid JSON only in this exact format:

{
  "explanation": "your explanation here"
}
Attraction:
{place.get("name")}

Category:
{place.get("category")}

Distance from previous attraction:
{place.get("travel_from_previous_km")} km

Ranking score:
{place.get("score")}

Matched travelers:
{", ".join(place.get("matched_travelers", []))}

Matched interests:
{", ".join(place.get("matched_interests", []))}

Match count:
{place.get("match_count")}

Trip travelers:
{trip.get("travelers")}

Explain the selection in 2-4 bullet points.
"""

    result = generate(prompt)

    if not isinstance(result, dict):
        return "Unable to generate an explanation."

    return result.get("explanation", "Unable to generate an explanation.")