import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query, Request, status

from backend.services.auth.authorization import extract_user_id, verify_trip_access
from backend.services.storage.activity_store import (
    list_trip_activity,
    list_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
)
from backend.models.activity import (
    ActivityFeedResponse,
    NotificationListResponse,
    UnreadCountResponse,
    MarkReadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Activity and Notifications"])


@router.get("/trip/{trip_id}/activity", response_model=ActivityFeedResponse)
@router.get("/activity/{trip_id}", response_model=ActivityFeedResponse)
def get_trip_activity_feed(
    trip_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Retrieves chronological activity events for an authorized trip.
    Enforces membership isolation: unauthenticated strangers are blocked.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    activities, total = list_trip_activity(
        trip_id=trip_id,
        limit=limit,
        offset=offset,
    )

    return ActivityFeedResponse(
        activities=activities,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(activities) < total),
    )


@router.get("/notifications", response_model=NotificationListResponse)
def get_user_notifications(
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    trip_id: Optional[str] = Query(None, description="Optional trip scoping"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Retrieves in-app notifications for the authenticated user.
    Never exposes notifications of other users.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view notifications",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If trip_id provided, verify trip access to prevent leaking private trip context
    if trip_id:
        verify_trip_access(trip_id, uid, required_role="viewer")

    notifs, total, unread_count = list_user_notifications(
        user_id=uid,
        is_read=is_read,
        trip_id=trip_id,
        limit=limit,
        offset=offset,
    )

    return NotificationListResponse(
        notifications=notifs,
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
        has_more=(offset + len(notifs) < total),
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def get_unread_notification_count(
    trip_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Quick count endpoint for notification badge UI.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if trip_id:
        verify_trip_access(trip_id, uid, required_role="viewer")

    _, _, unread_count = list_user_notifications(
        user_id=uid,
        is_read=False,
        trip_id=trip_id,
        limit=1,
        offset=0,
    )

    return UnreadCountResponse(unread_count=unread_count)


@router.patch("/notifications/{notification_id}/read", response_model=MarkReadResponse)
@router.put("/notifications/{notification_id}/read", response_model=MarkReadResponse)
def mark_single_notification_read(
    notification_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Marks a notification as read.
    Enforces strict ownership: only the owner of the notification can mark it read.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        mark_notification_read(notification_id=notification_id, user_id=uid)
        return MarkReadResponse(success=True, affected=1)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/notifications/mark-all-read", response_model=MarkReadResponse)
def mark_all_user_notifications_read(
    trip_id: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Marks all notifications as read for the authenticated user (optionally scoped to a trip).
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    affected = mark_all_notifications_read(user_id=uid, trip_id=trip_id)
    return MarkReadResponse(success=True, affected=affected)
