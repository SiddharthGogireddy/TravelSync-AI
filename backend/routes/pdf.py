from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import FileResponse
import os
from typing import Optional
from backend.services.storage.trip_store import load_trip
from backend.services.pdf.pdf_generator import generate_pdf
from backend.services.auth.authorization import extract_user_id, verify_trip_access

router = APIRouter(
    prefix="/trip",
    tags=["PDF"],
)


@router.get("/{trip_id}/pdf")
def download_pdf(
    trip_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    trip = trip_record.get("data")

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    if isinstance(trip, dict) and "trip" in trip and isinstance(trip["trip"], dict):
        trip_data = trip["trip"].copy()
    else:
        trip_data = trip.copy() if isinstance(trip, dict) else {}
    trip_data["trip_id"] = trip_id

    from backend.services.storage.note_store import get_notes
    if not trip_data.get("notes"):
        trip_data["notes"] = get_notes(trip_id) or trip.get("notes", [])

    filename = generate_pdf(trip_data)
    

    return FileResponse(
        filename,
        media_type="application/pdf",
        filename=os.path.basename(filename)
    )