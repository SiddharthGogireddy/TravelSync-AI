import logging
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.gemini_service import generate

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_CATEGORIES = {"food", "travel", "hotel", "shopping", "activities"}

def fallback_categorize(title: str) -> str:
    title_lower = (title or "").lower().strip()
    keywords = {
        "travel": ["flight", "plane", "train", "cab", "taxi", "uber", "lyft", "bus", "metro", "subway", "fuel", "gas", "petrol", "fare", "toll", "ticket", "transport", "ride"],
        "food": ["food", "dinner", "lunch", "breakfast", "brunch", "meal", "cafe", "coffee", "restaurant", "drinks", "drink", "bar", "snack", "pizza", "burger", "grocery", "groceries", "supermarket"],
        "hotel": ["hotel", "hostel", "motel", "resort", "airbnb", "stay", "room", "lodging", "accommodation", "checkin", "checkout"],
        "shopping": ["shopping", "mall", "clothes", "clothing", "souvenir", "souvenirs", "gift", "gifts", "store", "shop", "market", "shoes", "duty free", "bag", "bags", "purchase", "buy", "boutique"],
        "activities": ["activity", "activities", "museum", "tour", "sightseeing", "attraction", "park", "safari", "scuba", "diving", "hike", "hiking", "guide", "show", "concert", "monument"],
    }
    for cat, kws in keywords.items():
        if any(kw in title_lower for kw in kws):
            return cat
    return "food"

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
    title = (data.title or "").strip()
    if not title:
        return {"category": "food"}

    category = None
    try:
        prompt = f"""
Classify this expense into ONE category:
food, travel, hotel, shopping, activities

Expense: {title}

Return ONLY the category name.
"""
        raw_result = generate(prompt)
        if isinstance(raw_result, str):
            clean = raw_result.strip().lower().strip('"`\'.,;:')
            for candidate in clean.split():
                cand = candidate.strip('"`\'.,;:')
                if cand in VALID_CATEGORIES:
                    category = cand
                    break
            if not category and clean in VALID_CATEGORIES:
                category = clean
        elif isinstance(raw_result, dict):
            val = str(raw_result.get("category", "")).strip().lower()
            if val in VALID_CATEGORIES:
                category = val
    except Exception as e:
        logger.warning(f"AI categorization failed for '{title}': {e}")

    if not category or category not in VALID_CATEGORIES:
        category = fallback_categorize(title)

    return {"category": category}