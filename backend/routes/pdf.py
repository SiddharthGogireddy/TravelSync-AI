from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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

    print("Trip loaded successfully")

    filename = (
    f"{trip['trip']['destination']}_trip.pdf"
)

    generate_pdf(
        trip["trip"],
        filename,
    )

    return FileResponse(
        filename,
        media_type="application/pdf",
        filename="trip.pdf",
    )