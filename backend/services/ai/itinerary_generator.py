from services.ai.prompt_builder import build_prompt


async def generate_itinerary(trip_data):
    prompt = build_prompt(trip_data)

    return {
        "prompt": prompt,
        "itinerary": "AI itinerary generation will be implemented in the next step."
    }