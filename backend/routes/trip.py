from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import (
    FileResponse,
)
from backend.services.storage.note_store import (
    get_notes,
    add_note,
    delete_note,
)
from backend.services.storage.favorite_store import (
    add_favorite,
    remove_favorite,
    is_favorite,
)
from backend.services.storage.trip_store import load_trip

router = APIRouter(
    prefix="/trip",
    tags=["Trip"]
)


@router.get("/{trip_id}")
def get_trip(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return trip

@router.post("/{trip_id}/favorite")
def favorite_trip(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    add_favorite(trip_id)

    return {
        "trip_id": trip_id,
        "favorite": True
    }


@router.delete("/{trip_id}/favorite")
def unfavorite_trip(trip_id: str):
    remove_favorite(trip_id)

    return {
        "trip_id": trip_id,
        "favorite": False
    }


@router.get("/{trip_id}/favorite")
def check_favorite(trip_id: str):
    return {
        "trip_id": trip_id,
        "favorite": is_favorite(trip_id)
    }
@router.get("/{trip_id}/notes")
def get_trip_notes(trip_id: str):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return {
        "trip_id": trip_id,
        "notes": get_notes(trip_id)
    }


@router.post("/{trip_id}/notes")
def create_trip_note(
    trip_id: str,
    note: str
):
    trip = load_trip(trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    if not note.strip():
        raise HTTPException(
            status_code=400,
            detail="Note cannot be empty"
        )

    notes = add_note(
        trip_id,
        note.strip()
    )

    return {
        "trip_id": trip_id,
        "notes": notes
    }


@router.delete("/{trip_id}/notes/{note_index}")
def remove_trip_note(
    trip_id: str,
    note_index: int
):
    deleted = delete_note(
        trip_id,
        note_index
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Note not found"
        )

    return {
        "trip_id": trip_id,
        "deleted": True
    }