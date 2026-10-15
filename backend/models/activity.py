from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ActivityEventResponse(BaseModel):
    id: str
    trip_id: str
    actor_id: str
    actor_name: Optional[str] = None
    event_type: str
    title: str
    summary: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    link: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class ActivityFeedResponse(BaseModel):
    activities: List[ActivityEventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class NotificationResponse(BaseModel):
    id: str
    notification_id: str
    user_id: str
    trip_id: str
    event_id: Optional[str] = None
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = False
    read_at: Optional[str] = None
    created_at: str


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int
    has_more: bool


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    success: bool
    affected: int = 1
