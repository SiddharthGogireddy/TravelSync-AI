from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


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
    start_date: Optional[str] = Field(default=None, description="Travel start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="Travel end date (YYYY-MM-DD)")
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
    user_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_travel_dates(self):
        # If either start_date or end_date is provided, validate both
        if self.start_date is not None or self.end_date is not None:
            if not self.start_date or not self.end_date:
                raise ValueError("Both start_date and end_date must be provided when specifying travel dates")

            try:
                dt_start = datetime.strptime(self.start_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("start_date must be in YYYY-MM-DD format")

            try:
                dt_end = datetime.strptime(self.end_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("end_date must be in YYYY-MM-DD format")

            if dt_end < dt_start:
                raise ValueError("end_date cannot precede start_date")

            date_days = (dt_end - dt_start).days + 1
            if date_days < 1 or date_days > 30:
                raise ValueError(f"Trip duration ({date_days} days) must be between 1 and 30 days")

            # Harmonize days with calculated travel date duration
            self.days = date_days

        return self
