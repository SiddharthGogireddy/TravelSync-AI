from services.ai.prompt_builder import build_prompt
from services.ai.gemini_service import generate

async def generate_itinerary(trip_data):
    prompt = build_prompt(trip_data)
    itinerary = await generate(prompt)
    return {
        "itinerary": itinerary
    }