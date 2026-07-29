from pydantic import BaseModel
from typing import List

class Traveler(BaseModel):
    name: str
    budget: float
    food_preference: str
    interests: List[str]
    mandatory_places: List[str]
    special_requirements: List[str]

class TripRequest(BaseModel):
    source: str
    destination: str
    start_date: str
    end_date: str
    travelers: List[Traveler]