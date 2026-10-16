from fastapi import APIRouter, Query
from typing import List, Dict, Any

from backend.services.external.location_service import (
    search_locations,
)

router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
)


@router.get("/search", response_model=List[Dict[str, Any]])
async def location_search(
    q: str = Query(
        ...,
        min_length=2,
        max_length=150,
        description="Location search query string",
    ),
    limit: int = Query(
        6,
        ge=1,
        le=10,
        description="Maximum number of location suggestions to return",
    ),
):
    """Search for locations worldwide using geocoding service with conservative caching."""
    if not q or not q.strip():
        return []

    return await search_locations(query=q.strip(), limit=limit)