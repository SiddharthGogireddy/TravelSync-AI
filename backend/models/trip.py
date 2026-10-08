from typing import List, Literal, Optional
from pydantic import BaseModel


class Traveler(BaseModel):
    name: str
    interests: List[str]
    budget: str
    pace: str


class MandatoryVisit(BaseModel):
    name: str
    day: int | None = None


class DestinationStop(BaseModel):
    name: str
    days: int = 1


class TripRequest(BaseModel):
    source: str
    destination: str
    days: int
    destinations: Optional[List[DestinationStop]] = None
    travelers: List[Traveler]
    mandatory_visits: List[MandatoryVisit] = []
    travel_mode: Literal[
        "car",
        "bus",
        "train",
        "flight"
    ]