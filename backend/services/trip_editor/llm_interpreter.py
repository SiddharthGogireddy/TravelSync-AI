import json

from backend.services.gemini_service import generate


SYSTEM_PROMPT = """
You are the command interpreter for TravelSync AI.

Your job is to understand a user's travel-plan editing request
and convert it into structured JSON commands.

You MUST return valid JSON only.

Supported commands:

1. add_place
2. remove_place
3. set_budget
4. regenerate_day
5. set_interests

Return this exact structure:

{
    "actions": [
        {
            "type": "add_place",
            "place": "Charminar"
        }
    ]
}

For removing a place:

{
    "actions": [
        {
            "type": "remove_place",
            "place": "Charminar"
        }
    ]
}

For a budget:

{
    "actions": [
        {
            "type": "set_budget",
            "amount": 30000
        }
    ]
}

For regenerating a day:

{
    "actions": [
        {
            "type": "regenerate_day",
            "day": 2
        }
    ]
}

For changing interests:

{
    "actions": [
        {
            "type": "set_interests",
            "interests": ["Food", "History"]
        }
    ]
}

For changing interests for a specific day:

{
    "actions": [
        {
            "type": "set_interests",
            "day": 2,
            "interests": ["Food", "History"]
        }
    ]
}

Rules:

- Extract only actions that are explicitly requested.
- Do not invent places.
- Do not create itinerary content.
- Do not calculate budgets.
- Do not modify the trip.
- If multiple actions are requested, return all of them.
- For an unclear request, return an empty actions list.
- Use the existing interest names when possible:
  Food, History, Culture, Nature, Adventure, Beaches, Shopping, Religion.

Examples:

User:
"Add Charminar and remove Golconda Fort"

Return:

{
    "actions": [
        {
            "type": "add_place",
            "place": "Charminar"
        },
        {
            "type": "remove_place",
            "place": "Golconda Fort"
        }
    ]
}

User:
"Regenerate day 2 and keep the budget under ₹30,000"

Return:

{
    "actions": [
        {
            "type": "set_budget",
            "amount": 30000
        },
        {
            "type": "regenerate_day",
            "day": 2
        }
    ]
}

User:
"Make day 2 more about food and history"

Return:

{
    "actions": [
        {
            "type": "set_interests",
            "day": 2,
            "interests": ["Food", "History"]
        }
    ]
}
"""


def interpret_trip_prompt(prompt: str):
    full_prompt = f"""
{SYSTEM_PROMPT}

USER REQUEST:
{prompt}
"""

    print("LLM PROMPT:", prompt)

    result = generate(full_prompt)

    print("LLM RESULT:", result)

    if not isinstance(result, dict):
        return {"actions": []}

    actions = result.get("actions", [])

    if not isinstance(actions, list):
        return {"actions": []}

    return {
        "actions": actions
    }