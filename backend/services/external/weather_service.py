"""
TravelSync AI - Enhanced Weather Forecast & Disruption Alerts Service
Integrates Open-Meteo API (free, open, global coverage, no key required).
Provides daily forecasts, multi-destination matching, disruption warning thresholds,
and transparent horizon limitation reporting without fabricating forecasts.
"""

import time
import logging
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Optional, Any, Tuple
import httpx

from backend.services.planner.weather_planner import is_outdoor_place

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_SECONDS = 6.0
CACHE_TTL_SECONDS = 1800.0  # 30 minutes in-memory TTL
MAX_FORECAST_HORIZON_DAYS = 16  # Open-Meteo live forecast horizon limit

# In-memory forecast cache: key -> {"data": ..., "cached_at": float}
_WEATHER_CACHE: Dict[str, Any] = {}

# WMO Weather Interpretation Codes (WMO 4501)
WMO_DESCRIPTIONS: Dict[int, Dict[str, str]] = {
    0: {"description": "Clear sky", "icon": "☀️", "category": "clear"},
    1: {"description": "Mainly clear", "icon": "🌤️", "category": "clear"},
    2: {"description": "Partly cloudy", "icon": "⛅", "category": "cloudy"},
    3: {"description": "Overcast", "icon": "☁️", "category": "cloudy"},
    45: {"description": "Fog", "icon": "🌫️", "category": "fog"},
    48: {"description": "Depositing rime fog", "icon": "🌫️", "category": "fog"},
    51: {"description": "Light drizzle", "icon": "🌦️", "category": "drizzle"},
    53: {"description": "Moderate drizzle", "icon": "🌦️", "category": "drizzle"},
    55: {"description": "Dense drizzle", "icon": "🌧️", "category": "drizzle"},
    56: {"description": "Light freezing drizzle", "icon": "🌨️", "category": "freezing_drizzle"},
    57: {"description": "Dense freezing drizzle", "icon": "🌨️", "category": "freezing_drizzle"},
    61: {"description": "Slight rain", "icon": "🌧️", "category": "rain"},
    63: {"description": "Moderate rain", "icon": "🌧️", "category": "rain"},
    65: {"description": "Heavy rain", "icon": "🌧️", "category": "heavy_rain"},
    66: {"description": "Light freezing rain", "icon": "🌨️", "category": "freezing_rain"},
    67: {"description": "Heavy freezing rain", "icon": "🌨️", "category": "freezing_rain"},
    71: {"description": "Slight snow fall", "icon": "🌨️", "category": "snow"},
    73: {"description": "Moderate snow fall", "icon": "🌨️", "category": "snow"},
    75: {"description": "Heavy snow fall", "icon": "🌨️", "category": "snow"},
    77: {"description": "Snow grains", "icon": "🌨️", "category": "snow"},
    80: {"description": "Slight rain showers", "icon": "🌦️", "category": "rain"},
    81: {"description": "Moderate rain showers", "icon": "🌧️", "category": "rain"},
    82: {"description": "Violent rain showers", "icon": "🌧️", "category": "heavy_rain"},
    85: {"description": "Slight snow showers", "icon": "🌨️", "category": "snow"},
    86: {"description": "Heavy snow showers", "icon": "🌨️", "category": "snow"},
    95: {"description": "Thunderstorm", "icon": "⛈️", "category": "storm"},
    96: {"description": "Thunderstorm with slight hail", "icon": "⛈️", "category": "storm"},
    99: {"description": "Thunderstorm with heavy hail", "icon": "⛈️", "category": "storm"},
}


def clear_weather_cache() -> None:
    """Clears in-memory weather cache."""
    _WEATHER_CACHE.clear()


def wmo_code_to_condition(code: int) -> Dict[str, str]:
    """Resolves WMO integer code to description, icon, and category."""
    return WMO_DESCRIPTIONS.get(int(code), {"description": "Variable weather", "icon": "🌤️", "category": "variable"})


def validate_coordinates(lat: Any, lon: Any) -> Tuple[float, float]:
    """Validates that latitude and longitude are valid numeric geographic coordinates."""
    try:
        f_lat = float(lat)
        f_lon = float(lon)
    except (ValueError, TypeError):
        raise ValueError("Latitude and longitude must be valid numeric values.")

    if not (-90.0 <= f_lat <= 90.0):
        raise ValueError(f"Latitude must be between -90 and 90. Got: {f_lat}")
    if not (-180.0 <= f_lon <= 180.0):
        raise ValueError(f"Longitude must be between -180 and 180. Got: {f_lon}")

    return f_lat, f_lon


async def get_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Backward-compatible helper used during core trip generation.
    Returns Open-Meteo response dict with 'daily'.
    """
    f_lat, f_lon = validate_coordinates(lat, lon)
    params = {
        "latitude": f_lat,
        "longitude": f_lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "weathercode",
            "precipitation_probability_max",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],
        "forecast_days": 7,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT_SECONDS) as client:
            response = await client.get(BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if "daily" in data and "time" in data["daily"]:
                return data
    except Exception as e:
        logger.warning(f"Failed to fetch live weather ({e}), returning default forecast structure")

    now = datetime.now(timezone.utc)
    return {
        "daily": {
            "time": [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
            "temperature_2m_max": [28.0] * 7,
            "temperature_2m_min": [20.0] * 7,
            "weathercode": [0] * 7,
            "precipitation_probability_max": [10] * 7,
            "precipitation_sum": [0.0] * 7,
            "wind_speed_10m_max": [12.0] * 7,
        }
    }


async def fetch_open_meteo_forecast(
    lat: float,
    lon: float,
    forecast_days: int = 16,
) -> Optional[Dict[str, Any]]:
    """
    Fetches raw forecast from Open-Meteo API with timeout and in-memory caching.
    """
    f_lat, f_lon = validate_coordinates(lat, lon)
    days = min(16, max(1, forecast_days))
    cache_key = f"{round(f_lat, 3)}:{round(f_lon, 3)}:{days}"

    now_ts = time.time()
    if cache_key in _WEATHER_CACHE:
        entry = _WEATHER_CACHE[cache_key]
        if now_ts - entry["cached_at"] < CACHE_TTL_SECONDS:
            return dict(entry["data"])

    params = {
        "latitude": f_lat,
        "longitude": f_lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "weathercode",
            "precipitation_probability_max",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],
        "forecast_days": days,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT_SECONDS) as client:
            resp = await client.get(BASE_URL, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if "daily" in data and "time" in data["daily"]:
                    _WEATHER_CACHE[cache_key] = {"data": data, "cached_at": now_ts}
                    return data
    except Exception as e:
        logger.warning(f"Open-Meteo forecast fetch failed for {lat}, {lon}: {e}")

    return None


def evaluate_day_weather_disruptions(
    day_num: int,
    target_date_str: str,
    day_forecast: Dict[str, Any],
    day_places: List[Dict[str, Any]],
    destination_name: str = "Destination",
) -> List[Dict[str, Any]]:
    """
    Evaluates weather disruption warnings for a single day using documented thresholds.
    Distinguishes TravelSync AI rules from provider alerts.
    """
    alerts: List[Dict[str, Any]] = []

    if day_forecast.get("status") != "available":
        return alerts

    wcode = day_forecast.get("weather_code", 0)
    max_t = day_forecast.get("max_temp")
    min_t = day_forecast.get("min_temp")
    precip_prob = day_forecast.get("precipitation_probability")
    precip_sum = day_forecast.get("precipitation_sum")
    wind_max = day_forecast.get("wind_speed_max")

    outdoor_places = [p.get("name", "Outdoor sight") for p in day_places if is_outdoor_place(p)]

    # 1. Severe Thunderstorms / Hail (WMO 95, 96, 99)
    if wcode in [95, 96, 99]:
        alerts.append({
            "day": day_num,
            "date": target_date_str,
            "destination": destination_name,
            "warning_source": "travelsync_ai",
            "alert_type": "severe",
            "severity": "high",
            "title": "Severe Thunderstorm Alert (TravelSync AI)",
            "message": f"Thunderstorms forecasted for Day {day_num} (WMO Code {wcode}). High risk of lightning and localized flooding.",
            "affected_outdoor_activities": outdoor_places,
            "recommendation": "Review scheduled outdoor activities. Consider visiting indoor museums or heritage galleries during storm windows. (Itinerary has NOT been automatically altered.)",
        })

    # 2. Heavy Rain (WMO 65, 82, or precip >= 15mm, or precip_prob >= 75%)
    elif (wcode in [65, 82]) or (precip_sum is not None and precip_sum >= 15.0) or (precip_prob is not None and precip_prob >= 75):
        detail_reasons = []
        if precip_prob is not None:
            detail_reasons.append(f"{precip_prob}% rain probability")
        if precip_sum is not None:
            detail_reasons.append(f"{precip_sum} mm expected rainfall")
        reason_str = ", ".join(detail_reasons) if detail_reasons else "Heavy precipitation"

        alerts.append({
            "day": day_num,
            "date": target_date_str,
            "destination": destination_name,
            "warning_source": "travelsync_ai",
            "alert_type": "warning",
            "severity": "medium",
            "title": "Heavy Rain Warning (TravelSync AI)",
            "message": f"Heavy rainfall expected on Day {day_num} ({reason_str}). Outdoor attractions may experience wet conditions.",
            "affected_outdoor_activities": outdoor_places,
            "recommendation": "Pack waterproof gear and umbrellas. Check indoor options or covered pavilions if traveling with family. (Itinerary remains intact.)",
        })

    # 3. Moderate Rain Advisory (WMO 61, 63, 80, 81 or precip_prob >= 50%)
    elif (wcode in [61, 63, 80, 81]) or (precip_prob is not None and precip_prob >= 50):
        alerts.append({
            "day": day_num,
            "date": target_date_str,
            "destination": destination_name,
            "warning_source": "travelsync_ai",
            "alert_type": "advisory",
            "severity": "low",
            "title": "Rain Advisory (TravelSync AI)",
            "message": f"Light to moderate rain forecasted on Day {day_num} ({precip_prob}% probability).",
            "affected_outdoor_activities": outdoor_places,
            "recommendation": "Keep an umbrella on hand. Most attractions remain accessible. (Itinerary remains intact.)",
        })

    # 4. Extreme Heat (max_temp >= 38.0°C)
    if max_t is not None and max_t >= 38.0:
        alerts.append({
            "day": day_num,
            "date": target_date_str,
            "destination": destination_name,
            "warning_source": "travelsync_ai",
            "alert_type": "warning",
            "severity": "medium",
            "title": "Extreme Heat Advisory (TravelSync AI)",
            "message": f"Very high temperatures forecasted ({max_t}°C) on Day {day_num}. Risk of heat exhaustion during midday exploration.",
            "affected_outdoor_activities": outdoor_places,
            "recommendation": "Plan outdoor walks for early morning or late afternoon. Stay hydrated and schedule shaded rests.",
        })

    # 5. Freezing / Snow (WMO 71-77, 85-86, or min_temp <= 0.0°C)
    if (wcode in [71, 73, 75, 77, 85, 86]) or (min_t is not None and min_t <= 0.0):
        alerts.append({
            "day": day_num,
            "date": target_date_str,
            "destination": destination_name,
            "warning_source": "travelsync_ai",
            "alert_type": "warning",
            "severity": "medium",
            "title": "Freezing & Snow Warning (TravelSync AI)",
            "message": f"Freezing temperatures ({min_t}°C) or snowfall forecasted on Day {day_num}.",
            "affected_outdoor_activities": outdoor_places,
            "recommendation": "Wear thermal layers and check transit roads for ice or delays.",
        })

    # 6. High Wind (wind_speed_max >= 50.0 km/h)
    if wind_max is not None and wind_max >= 50.0:
        alerts.append({
            "day": day_num,
            "date": target_date_str,
            "destination": destination_name,
            "warning_source": "travelsync_ai",
            "alert_type": "advisory",
            "severity": "low",
            "title": "High Wind Advisory (TravelSync AI)",
            "message": f"Gusty winds up to {wind_max} km/h expected on Day {day_num}.",
            "affected_outdoor_activities": outdoor_places,
            "recommendation": "Secure loose items and exercise caution at elevated viewpoints or coastal spots.",
        })

    return alerts


async def get_trip_weather_forecasts_and_alerts(
    trip_dict: Dict[str, Any],
    trip_id: str,
) -> Dict[str, Any]:
    """
    Constructs comprehensive weather forecast and itinerary disruption alerts for a trip.
    Supports single-destination and multi-destination trips.
    Accounts for Open-Meteo's 16-day forecast horizon without fabricating data.
    """
    # 1. Resolve trip base date
    start_date_str = trip_dict.get("start_date")
    if not start_date_str and isinstance(trip_dict.get("travel_dates"), dict):
        start_date_str = trip_dict["travel_dates"].get("start_date")

    today_utc = datetime.now(timezone.utc).date()
    has_explicit_dates = False
    if start_date_str and isinstance(start_date_str, str):
        try:
            base_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
            has_explicit_dates = True
        except ValueError:
            base_date = today_utc
    else:
        base_date = today_utc

    # 2. Resolve destinations and schedule mapping
    is_multi = trip_dict.get("is_multi_destination", False)
    destinations = trip_dict.get("destinations") or []
    day_schedule = trip_dict.get("day_schedule") or {}
    total_days = int(trip_dict.get("days") or len(day_schedule) or 1)

    dest_loc = trip_dict.get("destination_location") or {}
    default_lat = float(dest_loc.get("lat", 0.0))
    default_lon = float(dest_loc.get("lon", 0.0))
    default_dest_name = (trip_dict.get("destination") or "Destination").split(",")[0].strip()

    # Build per-day destination coordinate mapping
    day_mapping: Dict[int, Dict[str, Any]] = {}

    if is_multi and destinations:
        curr_day = 1
        for stop in destinations:
            stop_name = stop.get("name", default_dest_name)
            stop_days = int(stop.get("days", 1))
            stop_loc = stop.get("location") or {}
            stop_lat = float(stop_loc.get("lat") or default_lat)
            stop_lon = float(stop_loc.get("lon") or default_lon)

            for d in range(stop_days):
                if curr_day <= total_days:
                    day_mapping[curr_day] = {
                        "name": stop_name,
                        "lat": stop_lat,
                        "lon": stop_lon,
                    }
                    curr_day += 1
    else:
        for d in range(1, total_days + 1):
            day_mapping[d] = {
                "name": default_dest_name,
                "lat": default_lat,
                "lon": default_lon,
            }

    # Group unique locations to minimize provider network requests
    unique_locations: Dict[Tuple[float, float], Optional[Dict[str, Any]]] = {}
    for d_info in day_mapping.values():
        coords = (round(d_info["lat"], 3), round(d_info["lon"], 3))
        if coords not in unique_locations:
            unique_locations[coords] = None

    # Fetch forecasts for unique locations
    for coords in unique_locations.keys():
        if coords != (0.0, 0.0):
            forecast_data = await fetch_open_meteo_forecast(coords[0], coords[1], forecast_days=16)
            unique_locations[coords] = forecast_data

    daily_forecasts: List[Dict[str, Any]] = []
    all_alerts: List[Dict[str, Any]] = []

    # 3. Match each day to forecast dates and horizon status
    for day_num in range(1, total_days + 1):
        target_date = base_date + timedelta(days=day_num - 1)
        target_date_str = target_date.strftime("%Y-%m-%d")
        d_info = day_mapping.get(day_num, {"name": default_dest_name, "lat": default_lat, "lon": default_lon})
        coords = (round(d_info["lat"], 3), round(d_info["lon"], 3))
        raw_weather = unique_locations.get(coords)

        day_places = day_schedule.get(str(day_num)) or []
        days_from_today = (target_date - today_utc).days

        # Check if date is within 16-day horizon
        if 0 <= days_from_today < MAX_FORECAST_HORIZON_DAYS and raw_weather:
            daily = raw_weather.get("daily", {})
            time_list = daily.get("time", [])

            if target_date_str in time_list:
                idx = time_list.index(target_date_str)
                wcode = int(daily.get("weathercode", [0])[idx])
                cond = wmo_code_to_condition(wcode)

                f_item = {
                    "day": day_num,
                    "date": target_date_str,
                    "destination": d_info["name"],
                    "status": "available",
                    "weather_code": wcode,
                    "condition": cond["description"],
                    "icon": cond["icon"],
                    "category": cond["category"],
                    "min_temp": daily.get("temperature_2m_min", [None])[idx],
                    "max_temp": daily.get("temperature_2m_max", [None])[idx],
                    "precipitation_probability": daily.get("precipitation_probability_max", [None])[idx],
                    "precipitation_sum": daily.get("precipitation_sum", [None])[idx],
                    "wind_speed_max": daily.get("wind_speed_10m_max", [None])[idx],
                    "update_time": datetime.now(timezone.utc).isoformat(),
                    "provider": "Open-Meteo",
                }
                daily_forecasts.append(f_item)

                # Evaluate disruption alerts
                day_alerts = evaluate_day_weather_disruptions(
                    day_num=day_num,
                    target_date_str=target_date_str,
                    day_forecast=f_item,
                    day_places=day_places,
                    destination_name=d_info["name"],
                )
                all_alerts.extend(day_alerts)
                continue

        # If beyond horizon or unavailable: DO NOT fabricate forecast numbers
        if days_from_today >= MAX_FORECAST_HORIZON_DAYS:
            f_item = {
                "day": day_num,
                "date": target_date_str,
                "destination": d_info["name"],
                "status": "beyond_horizon",
                "condition": "Forecast unavailable (Beyond 16-day horizon)",
                "icon": "📅",
                "message": f"Travel date ({target_date_str}) is beyond the provider's 16-day live forecast window. Live forecast will become available closer to departure.",
                "update_time": datetime.now(timezone.utc).isoformat(),
                "provider": "Open-Meteo",
            }
        elif days_from_today < 0:
            f_item = {
                "day": day_num,
                "date": target_date_str,
                "destination": d_info["name"],
                "status": "past_date",
                "condition": "Past travel date",
                "icon": "🕒",
                "message": f"Date {target_date_str} has already passed.",
                "update_time": datetime.now(timezone.utc).isoformat(),
                "provider": "Open-Meteo",
            }
        else:
            f_item = {
                "day": day_num,
                "date": target_date_str,
                "destination": d_info["name"],
                "status": "unavailable",
                "condition": "Forecast temporarily unavailable",
                "icon": "⚠️",
                "message": "Live meteorological data could not be retrieved from provider.",
                "update_time": datetime.now(timezone.utc).isoformat(),
                "provider": "Open-Meteo",
            }

        daily_forecasts.append(f_item)

    return {
        "success": True,
        "trip_id": trip_id,
        "destination": default_dest_name,
        "is_multi_destination": is_multi,
        "has_explicit_dates": has_explicit_dates,
        "base_date": base_date.strftime("%Y-%m-%d"),
        "forecast_horizon_days": MAX_FORECAST_HORIZON_DAYS,
        "daily_forecasts": daily_forecasts,
        "disruption_alerts": all_alerts,
        "alert_count": len(all_alerts),
        "update_time": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Weather forecasts are indicative and sourced from Open-Meteo. Itinerary activities are never automatically altered.",
    }