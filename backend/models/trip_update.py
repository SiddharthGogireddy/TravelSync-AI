from typing import Optional

from pydantic import BaseModel


class TripUpdateRequest(BaseModel):

    budget: Optional[int] = None

    add_place: Optional[str] = None

    remove_place: Optional[str] = None

    regenerate_day: Optional[int] = None