from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.services.auth.authorization import verify_trip_access, extract_user_id
from backend.services.sharing.invitation_service import (
    create_invitation,
    list_trip_invitations,
    revoke_invitation,
    get_invitation_preview,
    accept_invitation,
    decline_invitation,
)

router = APIRouter(tags=["Invitations"])


class CreateInvitationRequest(BaseModel):
    role: str = Field(default="viewer", description="Role to grant: 'viewer' or 'editor'")
    expires_in_days: int = Field(default=7, ge=1, le=90, description="Expiration in days (1-90)")


@router.post("/trip/{trip_id}/invitations", status_code=status.HTTP_201_CREATED)
def create_trip_invitation(
    trip_id: str,
    payload: CreateInvitationRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-ID header is missing",
        )

    # Enforce that only the trip owner can create invitations
    verify_trip_access(trip_id, uid, required_role="owner")

    try:
        invitation = create_invitation(
            trip_id=trip_id,
            owner_user_id=uid,
            role=payload.role,
            expires_in_days=payload.expires_in_days,
        )
        return invitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/trip/{trip_id}/invitations")
def get_trip_invitations(
    trip_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-ID header is missing",
        )

    verify_trip_access(trip_id, uid, required_role="owner")

    try:
        invitations = list_trip_invitations(trip_id=trip_id, requester_user_id=uid)
        return {"invitations": invitations}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/trip/{trip_id}/invitations/{invitation_id}")
def revoke_trip_invitation(
    trip_id: str,
    invitation_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-ID header is missing",
        )

    verify_trip_access(trip_id, uid, required_role="owner")

    revoked = revoke_invitation(trip_id, uid, invitation_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    return {"message": "Invitation revoked successfully"}


@router.get("/invitations/{token}")
@router.get("/invitations/{token}/preview")
def preview_invitation(token: str):
    try:
        preview = get_invitation_preview(token)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/invitations/{token}/accept")
def accept_trip_invitation(
    token: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required to accept an invitation (pass X-User-ID header)",
        )

    try:
        result = accept_invitation(token, uid)
        return result
    except ValueError as e:
        msg = str(e)
        if "Invalid invitation" in msg or "Trip no longer exists" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/invitations/{token}/decline")
def decline_trip_invitation(
    token: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    try:
        result = decline_invitation(token, uid)
        return result
    except ValueError as e:
        msg = str(e)
        if "Invalid invitation" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
