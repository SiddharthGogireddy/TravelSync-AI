from fastapi import APIRouter
from models.trip import TripRequest

router = APIRouter(prefix="/trip", tags=["Trip"])

@router.post("/plan")
def plan_trip(request: TripRequest):
    return {
        "status": "success",
        "message": "Trip received",
        "destination": request.destination,
        "travelers": len(request.travelers)
    }