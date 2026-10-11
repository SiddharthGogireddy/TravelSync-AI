from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Traveler(BaseModel):
    name: str
    interests: List[str]
    budget: str
    pace: str


class MandatoryVisit(BaseModel):
    name: str
    day: int | None = Field(default=None, ge=1, le=30, description="Day number for visit")


class DestinationStop(BaseModel):
    name: str
    days: int = Field(default=1, ge=1, le=30, description="Duration in days for this stop")


class PlanningConstraints(BaseModel):
    max_daily_distance_km: Optional[float] = None
    max_budget: Optional[float] = None
    min_attractions_per_day: Optional[int] = None
    preferred_travel_mode: Optional[str] = None
    must_visit_locations: Optional[List[str]] = None
    locations_to_avoid: Optional[List[str]] = None
    must_visit: Optional[List[str]] = None
    avoided_locations: Optional[List[str]] = None
    preferred_pace: Optional[str] = None


class TripRequest(BaseModel):
    source: str
    destination: str
    days: int = Field(ge=1, le=30, description="Total trip duration in days (1 to 30)")
    destinations: Optional[List[DestinationStop]] = None
    travelers: List[Traveler]
    mandatory_visits: List[MandatoryVisit] = []
    constraints: Optional[PlanningConstraints] = None
    travel_mode: Literal[
        "car",
        "bus",
        "train",
        "flight"
    ]
