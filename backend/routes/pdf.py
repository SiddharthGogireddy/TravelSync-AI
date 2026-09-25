from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from backend.services.storage.trip_store import load_trip
from backend.services.pdf.pdf_generator import generate_pdf

router = APIRouter(
    prefix="/trip",
    tags=["PDF"],
)


@router.get("/{trip_id}/pdf")
def download_pdf(trip_id: str):

    print("Requested ID:", trip_id)

    trip = load_trip(trip_id)

    

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    trip_data = trip["trip"].copy()
    trip_data["trip_id"] = trip_id

    filename = generate_pdf(trip_data)
    

    return FileResponse(
        filename,
        media_type="application/pdf",
        filename=os.path.basename(filename)
    )