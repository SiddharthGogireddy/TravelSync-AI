from typing import List, Literal
from pydantic import BaseModel


class Traveler(BaseModel):
    name: str
    interests: List[str]
    budget: str
    pace: str


class MandatoryVisit(BaseModel):
    name: str
    day: int | None = None


class TripRequest(BaseModel):
    source: str
    destination: str
    
    days: int
    travelers: List[Traveler]
    mandatory_visits: List[MandatoryVisit] = []
    travel_mode: Literal[
        "car",
        "bus",
        "train",
        "flight"
    ]