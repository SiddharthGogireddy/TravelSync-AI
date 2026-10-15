from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Message text content")
    target_type: Optional[str] = Field(default="trip", description="'trip', 'attraction', or 'proposal'")
    target_id: Optional[str] = Field(default=None, max_length=256, description="Identifier for attraction or proposal")
    sender_name: Optional[str] = Field(default=None, max_length=128, description="Optional display name")
    sender_id: Optional[str] = Field(default=None, description="Client-supplied sender ID (forbidden for impersonation)")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank or whitespace-only")
        return cleaned

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v: Optional[str]) -> str:
        if not v:
            return "trip"
        norm = v.strip().lower()
        if norm not in ("trip", "attraction", "proposal"):
            raise ValueError("target_type must be 'trip', 'attraction', or 'proposal'")
        return norm


class ChatMessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Updated message content")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank or whitespace-only")
        return cleaned


class ChatMessageResponse(BaseModel):
    id: str
    message_id: str
    trip_id: str
    sender_id: str
    sender_name: Optional[str] = None
    content: str
    target_type: str = "trip"
    target_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    is_edited: bool = False
    is_deleted: bool = False


class ChatListResponse(BaseModel):
    messages: List[ChatMessageResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
