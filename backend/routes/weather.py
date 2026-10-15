"""
FastAPI Router for Weather Forecasts and Disruption Alerts
"""

from fastapi import APIRouter, HTTPException, Query, Header, Request
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.services.storage.trip_store import load_trip
from backend.services.auth.authorization import extract_user_id, verify_trip_access
import backend.services.external.weather_service as weather_service

router = APIRouter(
    prefix="/weather",
    tags=["Weather"],
)


@router.get("/forecast")
async def get_location_forecast(
    lat: float = Query(..., description="Latitude coordinate between -90 and 90"),
    lon: float = Query(..., description="Longitude coordinate between -180 and 180"),
    days: int = Query(default=7, ge=1, le=16, description="Forecast days (1 to 16)"),
) -> Dict[str, Any]:
    """
    Retrieves live daily forecast for specific geographic coordinates.
    """
    try:
        f_lat, f_lon = weather_service.validate_coordinates(lat, lon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw = await weather_service.fetch_open_meteo_forecast(f_lat, f_lon, forecast_days=days)
    if not raw or "daily" not in raw:
        return {
            "success": False,
            "status": "unavailable",
            "message": "Live meteorological data currently unavailable for coordinates.",
            "latitude": f_lat,
            "longitude": f_lon,
            "daily_forecasts": [],
            "update_time": datetime.now(timezone.utc).isoformat(),
        }

    daily = raw["daily"]
    time_list = daily.get("time", [])
    forecasts = []

    for i, t in enumerate(time_list):
        wcode = int(daily.get("weathercode", [0])[i]) if i < len(daily.get("weathercode", [])) else 0
        cond = weather_service.wmo_code_to_condition(wcode)
        forecasts.append({
            "date": t,
            "weather_code": wcode,
            "condition": cond["description"],
            "icon": cond["icon"],
            "category": cond["category"],
            "min_temp": daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
            "max_temp": daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
            "precipitation_probability": daily.get("precipitation_probability_max", [None])[i] if i < len(daily.get("precipitation_probability_max", [])) else None,
            "precipitation_sum": daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None,
            "wind_speed_max": daily.get("wind_speed_10m_max", [None])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None,
        })

    return {
        "success": True,
        "status": "available",
        "latitude": f_lat,
        "longitude": f_lon,
        "daily_forecasts": forecasts,
        "update_time": datetime.now(timezone.utc).isoformat(),
        "provider": "Open-Meteo",
    }


@router.get("/trip/{trip_id}/alerts")
async def get_trip_weather_alerts(
    trip_id: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Retrieves weather forecasts and disruption alerts tailored to the trip's destination(s) and dates.
    Identifies severe weather, distinguishes TravelSync AI warnings, and suggests indoor alternatives.
    """
    uid = extract_user_id(request, x_user_id, user_id, authorization)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    trip_data = trip_record.get("data")
    if trip_data is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    inner_trip = trip_data.get("trip", trip_data) if isinstance(trip_data, dict) else {}
    alerts_data = await weather_service.get_trip_weather_forecasts_and_alerts(inner_trip, trip_id)
    return alerts_data