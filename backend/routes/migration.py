import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, Query, Request, status
from pydantic import BaseModel, Field

from backend.services.auth.authorization import extract_authenticated_user_id
from backend.services.storage.migration_service import (
    get_legacy_trips_preview,
    create_trips_backup,
    claim_legacy_trip,
    batch_claim_legacy_trips,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Legacy Data Migration"])


class ClaimBatchRequest(BaseModel):
    trip_ids: Optional[List[str]] = Field(default=None, description="Optional list of trip IDs to claim; if omitted, claims all unowned trips")


@router.get("/trip/legacy/preview")
def preview_legacy_trips(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
):
    """
    Returns a read-only preview of unowned legacy trips without modifying any data.
    """
    uid = extract_authenticated_user_id(request=request, authorization=authorization, token=token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view legacy migration preview",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_legacy_trips_preview()


@router.post("/trip/legacy/backup")
def trigger_backup(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
):
    """
    Creates an explicit snapshot backup of trips storage.
    """
    uid = extract_authenticated_user_id(request=request, authorization=authorization, token=token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create trips backup",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_trips_backup(label="user_triggered")


@router.post("/trip/{trip_id}/claim-legacy")
def claim_single_legacy_trip(
    trip_id: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
):
    """
    Explicit claiming workflow: assigns ownership of an unowned legacy trip to the authenticated user.
    Creates an automatic backup snapshot before modification.
    Rejects claiming if trip is already owned.
    """
    uid = extract_authenticated_user_id(request=request, authorization=authorization, token=token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: valid Bearer credentials needed to claim a trip",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        result = claim_legacy_trip(trip_id=trip_id, new_owner_id=uid)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/trip/legacy/claim-batch")
def claim_batch_legacy_trips(
    payload: ClaimBatchRequest,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
):
    """
    Batch claims eligible unowned legacy trips for the authenticated user with automated backup.
    """
    uid = extract_authenticated_user_id(request=request, authorization=authorization, token=token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to batch-claim legacy trips",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = batch_claim_legacy_trips(target_owner_id=uid, trip_ids=payload.trip_ids)
    return result
