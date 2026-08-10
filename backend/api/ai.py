from fastapi import APIRouter
from pydantic import BaseModel
from services.gemini_service import generate

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
Create a detailed {data.days}-day travel itinerary for {data.location}.

Budget: {data.budget}
Travelers: {data.travelers}
Interests: {", ".join(data.interests)}

Include:
- Day-wise plan
- Places
- Food suggestions
- Travel tips
"""

    result = generate(prompt)
    return {"itinerary": result}



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