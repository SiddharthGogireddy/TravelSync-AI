from services.ai.prompt_builder import build_prompt
from services.ai.gemini_service import generate
from services.ai.itinerary_validator import validate_itinerary
async def generate_itinerary(trip_data):
    prompt = build_prompt(trip_data)
    MAX_RETRIES = 2

    for _ in range(MAX_RETRIES):
        itinerary = await generate(prompt)

        validation = validate_itinerary(
            itinerary,
            trip_data
        )
        if validation["valid"]:
            break

    validation = validate_itinerary(itinerary, trip_data)
    return {
        "itinerary": itinerary,
        "validation": validation
    }
    