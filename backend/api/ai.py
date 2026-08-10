from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.gemini_service import generate

router = APIRouter()

class ItineraryRequest(BaseModel):
    location: str
    days: int
    budget: str
    travelers: int
    interests: list[str]

@router.post("/ai/itinerary")
def ai_itinerary(data: ItineraryRequest):
    prompt = f"""
Generate a {data.days}-day travel itinerary for {data.location} for {data.travelers} people with a budget of ₹{data.budget}.

IMPORTANT:
Return ONLY valid JSON. No markdown, no explanation.

Format:
{{
  "days": [
    {{
      "day": 1,
      "title": "string",
      "activities": ["string"],
      "food": ["string"],
      "budget": "string"
    }}
  ]
}}
"""
    result = generate(prompt)
    return result



class InsightRequest(BaseModel):
    expenses: list

@router.post("/ai/insights")
def ai_insights(data: InsightRequest):
    prompt = f"""
Analyze this trip expense data:

{data.expenses}

Return:
- overspending areas
- saving tips
- patterns
"""

    result = generate(prompt)
    return {"insights": result}

class ChatRequest(BaseModel):
    message: str
    context: dict

@router.post("/ai/chat")
def ai_chat(data: ChatRequest):
    prompt = f"""
User question: {data.message}

Trip context:
{data.context}

Answer clearly and helpfully.
"""

    result = generate(prompt)
    return {"reply": result}

class CategoryRequest(BaseModel):
    title: str

@router.post("/ai/categorize")
def categorize(data: CategoryRequest):
    prompt = f"""
Classify this expense into ONE category:
food, travel, hotel, shopping, activities

Expense: {data.title}

Return ONLY the category name.
"""

    result = generate(prompt).strip().lower()
    return {"category": result}