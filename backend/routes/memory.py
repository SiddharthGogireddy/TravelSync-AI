import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse

from backend.services.auth.authorization import extract_user_id, verify_trip_access
from backend.services.storage.memory_store import (
    create_entry,
    list_entries,
    list_album_entries,
    get_journal_entries_for_export,
    get_entry,
    update_entry,
    delete_entry,
    save_memory_photo,
    get_memory_photo_path,
    MAX_PHOTO_SIZE_BYTES,
)
from backend.models.memory import (
    JournalEntryCreate,
    JournalEntryUpdate,
    JournalEntryResponse,
    JournalListResponse,
    PhotoUploadResponse,
    AlbumItemResponse,
    MemoryAlbumResponse,
)
from backend.services.storage.activity_store import record_activity
from backend.services.pdf.journal_pdf_generator import generate_journal_pdf

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Travel Memories and Trip Journal"])


@router.get("/trip/{trip_id}/journal", response_model=JournalListResponse)
def get_trip_journal(
    trip_id: str,
    day_number: Optional[int] = Query(None, ge=1, le=365, description="Filter memories by itinerary day"),
    attraction_name: Optional[str] = Query(None, description="Filter memories by attraction reference"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Lists chronological trip journal memories.
    Privacy rules:
    - Shared memories (is_private=False) are visible to all authorized trip members.
    - Private memories (is_private=True) are visible ONLY to the entry author.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    entries, total = list_entries(
        trip_id=trip_id,
        requester_id=uid or "",
        day_number=day_number,
        attraction_name=attraction_name,
        limit=limit,
        offset=offset,
    )

    return JournalListResponse(
        entries=entries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(entries) < total),
    )


@router.post("/trip/{trip_id}/journal", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def create_trip_journal_entry(
    trip_id: str,
    payload: JournalEntryCreate,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Creates a persistent journal memory for a trip, optionally tagged with an itinerary day or attraction.
    Derives author identity strictly from verified credentials.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    trip_record, role = verify_trip_access(trip_id, uid, required_role="viewer")

    # Determine author display name
    author_name = uid
    if trip_record:
        members = trip_record.get("members") or {}
        if uid in members and members[uid].get("name"):
            author_name = members[uid]["name"]
        elif trip_record.get("owner_id") == uid and trip_record.get("owner_name"):
            author_name = trip_record["owner_name"]

    try:
        entry = create_entry(
            trip_id=trip_id,
            author_id=uid,
            content=payload.content,
            author_name=author_name,
            day_number=payload.day_number,
            attraction_name=payload.attraction_name,
            title=payload.title,
            photo_url=payload.photo_url,
            photo_filename=payload.photo_filename,
            is_private=payload.is_private,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Activity feed integration:
    # Only public/shared entries produce activity events.
    # NEVER expose private journal text in notifications or activity feed.
    if not payload.is_private:
        try:
            day_suffix = f" for Day {payload.day_number}" if payload.day_number else ""
            attr_suffix = f" at {payload.attraction_name}" if payload.attraction_name else ""
            summary_text = f"{author_name} added a memory to the trip journal{day_suffix}{attr_suffix}"
            record_activity(
                trip_id=trip_id,
                actor_id=uid,
                event_type="journal_entry_created",
                title="New Trip Memory",
                summary=summary_text,
                target_type="journal",
                target_id=entry["id"],
                link=f"/trip/{trip_id}#section-journal",
                actor_name=author_name,
                notify_members=True,
            )
        except Exception as e:
            logger.warning(f"Could not record activity event for journal entry: {e}")

    return entry


@router.post("/trip/{trip_id}/journal/upload-photo", response_model=PhotoUploadResponse)
async def upload_journal_photo(
    trip_id: str,
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Uploads and validates a photo attachment for journal memories.
    Enforces image format, magic bytes, max 5MB size limit, and path traversal prevention.
    Stores photo binary securely on disk outside of trip JSON files.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded photo: {e}",
        )

    if len(file_bytes) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Photo size exceeds maximum allowed limit of {MAX_PHOTO_SIZE_BYTES // (1024 * 1024)}MB",
        )

    try:
        safe_filename, photo_url, size_bytes = save_memory_photo(
            file_bytes=file_bytes,
            original_filename=file.filename or "photo.jpg",
            content_type=file.content_type,
            trip_id=trip_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    content_type = file.content_type or mimetypes.guess_type(safe_filename)[0] or "image/jpeg"

    return PhotoUploadResponse(
        photo_url=photo_url,
        photo_filename=safe_filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )


@router.get("/trip/{trip_id}/journal/photos/{filename}")
def get_journal_photo(
    trip_id: str,
    filename: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Streams a securely stored photo memory file.
    Validates trip membership and ownership/privacy controls.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    file_path = get_memory_photo_path(filename)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    guessed_type, _ = mimetypes.guess_type(str(file_path))
    media_type = guessed_type or "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.put("/trip/{trip_id}/journal/{entry_id}", response_model=JournalEntryResponse)
def update_trip_journal_entry(
    trip_id: str,
    entry_id: str,
    payload: JournalEntryUpdate,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Edits a journal entry. Enforces that only the author can modify their own memory.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    existing = get_entry(entry_id)
    if not existing or existing.get("trip_id") != str(trip_id).strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")

    try:
        updated = update_entry(
            entry_id=entry_id,
            author_id=uid,
            title=payload.title,
            content=payload.content,
            day_number=payload.day_number,
            attraction_name=payload.attraction_name,
            photo_url=payload.photo_url,
            photo_filename=payload.photo_filename,
            is_private=payload.is_private,
        )
        return updated
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/trip/{trip_id}/journal/{entry_id}")
def delete_trip_journal_entry(
    trip_id: str,
    entry_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Deletes a journal entry. Only the author or the trip owner is authorized to delete it.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    trip_record, role = verify_trip_access(trip_id, uid, required_role="viewer")

    existing = get_entry(entry_id)
    if not existing or existing.get("trip_id") != str(trip_id).strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")

    is_owner = (role == "owner")
    try:
        delete_entry(entry_id=entry_id, requester_id=uid, is_owner=is_owner)
        return {"success": True, "id": entry_id, "deleted": True}
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/trip/{trip_id}/memories/album", response_model=MemoryAlbumResponse)
@router.get("/trip/{trip_id}/journal/album", response_model=MemoryAlbumResponse)
def get_trip_memory_album(
    trip_id: str,
    day_number: Optional[int] = Query(None, ge=1, le=365, description="Filter album photos by itinerary day"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Retrieves chronological photo memories for the trip album.
    Privacy rules:
    - Shared photos (is_private=False) are visible to all authorized trip members.
    - Private photos (is_private=True) are visible ONLY to the photo entry author.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    verify_trip_access(trip_id, uid, required_role="viewer")

    items, total = list_album_entries(
        trip_id=trip_id,
        requester_id=uid or "",
        day_number=day_number,
        limit=limit,
        offset=offset,
    )

    return MemoryAlbumResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items) < total),
    )


@router.get("/trip/{trip_id}/journal/pdf")
@router.get("/trip/{trip_id}/pdf/journal")
def export_trip_journal_pdf(
    trip_id: str,
    day_number: Optional[int] = Query(None, ge=1, le=365, description="Filter exported memories by itinerary day"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
    request: Request = None,
):
    """
    Generates and downloads an authenticated PDF export of the trip journal.
    Enforces strict privacy: private entries are excluded unless the requester is their author.
    Validates photo paths to ensure no arbitrary local file traversal.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization, token)
    trip_record, role = verify_trip_access(trip_id, uid, required_role="viewer")

    entries = get_journal_entries_for_export(
        trip_id=trip_id,
        requester_id=uid or "",
        day_number=day_number,
    )

    # Determine requester display name and trip details
    requester_name = uid or "Traveler"
    trip_data = trip_record.get("data") or {}
    if isinstance(trip_data, dict) and "trip" in trip_data and isinstance(trip_data["trip"], dict):
        inner_trip = trip_data["trip"]
    elif isinstance(trip_data, dict):
        inner_trip = trip_data
    else:
        inner_trip = {}

    members = trip_record.get("members") or {}
    if uid in members and members[uid].get("name"):
        requester_name = members[uid]["name"]
    elif trip_record.get("owner_id") == uid and trip_record.get("owner_name"):
        requester_name = trip_record["owner_name"]

    destination = inner_trip.get("destination") or "Destination"
    source = inner_trip.get("source") or ""
    trip_title = trip_record.get("title") or (f"{source} to {destination}" if source else destination)

    pdf_filepath = generate_journal_pdf(
        trip_id=trip_id,
        trip_title=trip_title,
        destination=destination,
        entries=entries,
        requester_name=requester_name,
        day_filter=day_number,
    )

    clean_dest = re.sub(r'[^\w\s-]', '', destination).strip().replace(" ", "_")
    download_filename = f"Journal_{clean_dest or 'Trip'}_{trip_id[:8]}.pdf"

    return FileResponse(
        pdf_filepath,
        media_type="application/pdf",
        filename=download_filename,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )

