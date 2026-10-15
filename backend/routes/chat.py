import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query, Request, status

from backend.services.auth.authorization import extract_user_id, verify_trip_access
from backend.services.storage.chat_store import (
    add_message,
    list_messages,
    get_message,
    update_message,
    delete_message,
)
from backend.models.chat import (
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatMessageResponse,
    ChatListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat and Comments"])


@router.get("/chat/{trip_id}", response_model=ChatListResponse)
@router.get("/trip/{trip_id}/chat", response_model=ChatListResponse)
def get_trip_chat(
    trip_id: str,
    target_type: Optional[str] = Query(None, description="Filter by 'trip', 'attraction', or 'proposal'"),
    target_id: Optional[str] = Query(None, description="Filter by target identifier (e.g. attraction name)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Retrieves chronological trip chat messages or attraction comments.
    Enforces trip membership and authorization on read requests.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    messages, total = list_messages(
        trip_id=trip_id,
        target_type=target_type,
        target_id=target_id,
        limit=limit,
        offset=offset,
    )

    return ChatListResponse(
        messages=messages,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(messages) < total),
    )


@router.post("/chat/{trip_id}", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
@router.post("/trip/{trip_id}/chat", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def post_trip_chat_message(
    trip_id: str,
    payload: ChatMessageCreate,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Sends a new trip chat message.
    Strictly derives sender identity from verified credentials.
    Rejects sender impersonation attempts.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to post messages",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject sender impersonation if client provided a conflicting sender_id in body
    if payload.sender_id is not None and str(payload.sender_id).strip() != uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sender impersonation rejected: cannot post as '{payload.sender_id}' when authenticated as '{uid}'",
        )

    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")

    try:
        msg = add_message(
            trip_id=trip_id,
            sender_id=uid,
            content=payload.content,
            sender_name=payload.sender_name or uid,
            target_type=payload.target_type or "trip",
            target_id=payload.target_id,
        )

        try:
            from backend.services.storage.activity_store import record_activity
            sender_name = payload.sender_name or uid
            record_activity(
                trip_id=trip_id,
                actor_id=uid,
                actor_name=sender_name,
                event_type="chat_message_posted",
                title="New Group Chat Message",
                summary=f"{sender_name} posted a message in group chat",
                target_type="chat",
                link=f"/trip/{trip_id}#section-chat",
                notify_members=True,
            )
        except Exception as e:
            logger.warning("Could not record chat_message_posted activity: %s", e)

        return msg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/chat/message/{message_id}", response_model=ChatMessageResponse)
@router.put("/chat/{trip_id}/message/{message_id}", response_model=ChatMessageResponse)
@router.put("/trip/{trip_id}/chat/{message_id}", response_model=ChatMessageResponse)
def edit_chat_message(
    message_id: str,
    payload: ChatMessageUpdate,
    trip_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Updates an existing chat message.
    Safe editing rule: Users may only edit messages they authored.
    """
    msg = get_message(message_id)
    if not msg or msg.get("is_deleted"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    target_trip_id = trip_id or msg["trip_id"]
    if target_trip_id != msg["trip_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip ID mismatch")

    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(target_trip_id, uid, required_role="viewer")

    if msg["sender_id"] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only edit your own messages",
        )

    try:
        updated = update_message(message_id=message_id, new_content=payload.content, sender_id=uid)
        return updated
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/chat/message/{message_id}")
@router.delete("/chat/{trip_id}/message/{message_id}")
@router.delete("/trip/{trip_id}/chat/{message_id}")
def delete_chat_message(
    message_id: str,
    trip_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Deletes an existing chat message.
    Safe deletion rules:
    - Senders can delete their own messages.
    - Trip owner can moderate/delete any message in the trip.
    - Others are denied with 403 Forbidden.
    """
    msg = get_message(message_id)
    if not msg or msg.get("is_deleted"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    target_trip_id = trip_id or msg["trip_id"]
    if target_trip_id != msg["trip_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trip ID mismatch")

    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    _, user_role = verify_trip_access(target_trip_id, uid, required_role="viewer")

    is_sender = (msg["sender_id"] == uid)
    is_owner = (user_role == "owner")

    if not (is_sender or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only delete your own messages unless you are the trip owner",
        )

    try:
        delete_message(message_id=message_id, user_id=uid, user_role=user_role)
        return {"success": True, "message_id": message_id, "deleted": True}
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ---------------------------------------------------------------------------
# Itinerary Attraction Comments Endpoints
# ---------------------------------------------------------------------------
@router.get("/trip/{trip_id}/attractions/{attraction_name}/comments", response_model=ChatListResponse)
def get_attraction_comments(
    trip_id: str,
    attraction_name: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Retrieves comments specifically associated with an itinerary attraction.
    """
    clean_attraction = str(attraction_name).strip()
    if not clean_attraction:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="attraction_name cannot be blank")

    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    messages, total = list_messages(
        trip_id=trip_id,
        target_type="attraction",
        target_id=clean_attraction,
        limit=limit,
        offset=offset,
    )

    return ChatListResponse(
        messages=messages,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(messages) < total),
    )


@router.post(
    "/trip/{trip_id}/attractions/{attraction_name}/comments",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_attraction_comment(
    trip_id: str,
    attraction_name: str,
    payload: ChatMessageCreate,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Adds a comment specifically associated with an itinerary attraction.
    """
    clean_attraction = str(attraction_name).strip()
    if not clean_attraction:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="attraction_name cannot be blank")

    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to post comments",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.sender_id is not None and str(payload.sender_id).strip() != uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sender impersonation rejected: cannot post as '{payload.sender_id}' when authenticated as '{uid}'",
        )

    verify_trip_access(trip_id, uid, required_role="viewer")

    try:
        msg = add_message(
            trip_id=trip_id,
            sender_id=uid,
            content=payload.content,
            sender_name=payload.sender_name or uid,
            target_type="attraction",
            target_id=clean_attraction,
        )

        try:
            from backend.services.storage.activity_store import record_activity
            sender_name = payload.sender_name or uid
            record_activity(
                trip_id=trip_id,
                actor_id=uid,
                actor_name=sender_name,
                event_type="attraction_comment_posted",
                title=f"New Comment on {clean_attraction}",
                summary=f"{sender_name} commented on {clean_attraction}",
                target_type="attraction",
                target_id=clean_attraction,
                link=f"/trip/{trip_id}#section-itinerary",
                notify_members=True,
            )
        except Exception as e:
            logger.warning("Could not record attraction_comment_posted activity: %s", e)

        return msg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
