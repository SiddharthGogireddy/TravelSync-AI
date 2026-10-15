from typing import Optional, List
from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Optional title or headline for the memory")
    content: str = Field(..., min_length=1, max_length=10000, description="Memory reflection or journal text")
    day_number: Optional[int] = Field(None, ge=1, le=365, description="Associated itinerary day number")
    attraction_name: Optional[str] = Field(None, max_length=200, description="Associated attraction name")
    photo_url: Optional[str] = Field(None, max_length=1024, description="Relative URL of the attached photo")
    photo_filename: Optional[str] = Field(None, max_length=256, description="Safe filename of the attached photo")
    is_private: bool = Field(False, description="Whether this memory is private to the author or shared with trip members")


class JournalEntryUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    day_number: Optional[int] = Field(None, ge=1, le=365)
    attraction_name: Optional[str] = Field(None, max_length=200)
    photo_url: Optional[str] = Field(None, max_length=1024)
    photo_filename: Optional[str] = Field(None, max_length=256)
    is_private: Optional[bool] = None


class JournalEntryResponse(BaseModel):
    id: str
    trip_id: str
    author_id: str
    author_name: Optional[str] = None
    day_number: Optional[int] = None
    attraction_name: Optional[str] = None
    title: Optional[str] = None
    content: str
    photo_url: Optional[str] = None
    photo_filename: Optional[str] = None
    is_private: bool = False
    created_at: str
    updated_at: Optional[str] = None


class JournalListResponse(BaseModel):
    entries: List[JournalEntryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class PhotoUploadResponse(BaseModel):
    photo_url: str
    photo_filename: str
    content_type: str
    size_bytes: int


class AlbumItemResponse(BaseModel):
    id: str
    trip_id: str
    author_id: str
    author_name: Optional[str] = None
    day_number: Optional[int] = None
    attraction_name: Optional[str] = None
    title: Optional[str] = None
    content: str
    photo_url: str
    photo_filename: str
    is_private: bool = False
    created_at: str


class MemoryAlbumResponse(BaseModel):
    items: List[AlbumItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

