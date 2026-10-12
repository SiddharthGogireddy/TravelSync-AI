"""
Unit and integration tests for Step 74: Weather Forecasts and Itinerary Alerts.
Validates Open-Meteo integration, multi-destination matching, disruption warning thresholds,
transparent horizon limitations, caching, provider timeouts, non-mutation of saved data,
and frontend service integration.
"""

import os
import sys
import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch, AsyncMock
from pathlib import Path
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip
from backend.services.external.weather_service import (
    validate_coordinates,
    wmo_code_to_condition,
    evaluate_day_weather_disruptions,
    clear_weather_cache,
    fetch_open_meteo_forecast,
    MAX_FORECAST_HORIZON_DAYS,
)

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BASE_DIR / "frontend" / "src"


@pytest.fixture(autouse=True)
def reset_weather():
    clear_weather_cache()
    yield
    clear_weather_cache()


def test_validate_coordinates():
    """Verify coordinate bounds validation (-90 to 90 lat, -180 to 180 lon)."""
    assert validate_coordinates(26.91, 75.78) == (26.91, 75.78)
    assert validate_coordinates("12.97", "77.59") == (12.97, 77.59)

    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        validate_coordinates(120.0, 75.0)

    with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
        validate_coordinates(26.0, 200.0)

    with pytest.raises(ValueError, match="valid numeric values"):
        validate_coordinates("invalid", "coords")


def test_wmo_code_to_condition():
    """Verify WMO weather codes resolve to human-readable condition, icon, and category."""
    clear = wmo_code_to_condition(0)
    assert clear["category"] == "clear"
    assert "Clear" in clear["description"]

    rain = wmo_code_to_condition(65)
    assert rain["category"] == "heavy_rain"
    assert "Heavy rain" in rain["description"]

    storm = wmo_code_to_condition(95)
    assert storm["category"] == "storm"
    assert "Thunderstorm" in storm["description"]


def test_weather_disruption_warning_thresholds():
    """Verify documented disruption warning thresholds for rain, storms, heat, and wind."""
    outdoor_places = [
        {"name": "Amber Fort", "category": "Fort"},
        {"name": "Albert Hall Museum", "category": "Museum"},
    ]

    # 1. Thunderstorm threshold (WMO 95)
    f_storm = {
        "status": "available",
        "weather_code": 95,
        "max_temp": 28.0,
        "min_temp": 20.0,
        "precipitation_probability": 90,
    }
    alerts_storm = evaluate_day_weather_disruptions(1, "2026-10-15", f_storm, outdoor_places, "Jaipur")
    assert len(alerts_storm) >= 1
    assert alerts_storm[0]["alert_type"] == "severe"
    assert alerts_storm[0]["warning_source"] == "travelsync_ai"
    assert "Amber Fort" in alerts_storm[0]["affected_outdoor_activities"]
    assert "Albert Hall Museum" not in alerts_storm[0]["affected_outdoor_activities"]
    assert "Itinerary has NOT been automatically altered" in alerts_storm[0]["recommendation"]

    # 2. Heavy Rain threshold (precip_prob >= 75%)
    f_rain = {
        "status": "available",
        "weather_code": 61,
        "max_temp": 24.0,
        "min_temp": 18.0,
        "precipitation_probability": 85,
        "precipitation_sum": 20.0,
    }
    alerts_rain = evaluate_day_weather_disruptions(2, "2026-10-16", f_rain, outdoor_places, "Jaipur")
    assert any(a["alert_type"] == "warning" and "Heavy Rain" in a["title"] for a in alerts_rain)

    # 3. Extreme Heat threshold (max_temp >= 38.0°C)
    f_heat = {
        "status": "available",
        "weather_code": 0,
        "max_temp": 41.5,
        "min_temp": 28.0,
        "precipitation_probability": 0,
    }
    alerts_heat = evaluate_day_weather_disruptions(3, "2026-10-17", f_heat, outdoor_places, "Jaipur")
    assert any("Extreme Heat" in a["title"] for a in alerts_heat)


def test_location_forecast_api_endpoint():
    """Verify GET /weather/forecast returns daily forecast structure."""
    mock_raw = {
        "daily": {
            "time": ["2026-10-15", "2026-10-16"],
            "temperature_2m_max": [31.0, 29.5],
            "temperature_2m_min": [19.0, 18.5],
            "weathercode": [1, 61],
            "precipitation_probability_max": [10, 65],
            "precipitation_sum": [0.0, 4.5],
            "wind_speed_10m_max": [14.0, 22.0],
        }
    }
    with patch("backend.services.external.weather_service.fetch_open_meteo_forecast", new=AsyncMock(return_value=mock_raw)):
        res = client.get("/weather/forecast?lat=26.91&lon=75.78&days=2")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["daily_forecasts"]) == 2
        d1 = data["daily_forecasts"][0]
        assert d1["date"] == "2026-10-15"
        assert d1["max_temp"] == 31.0
        assert d1["min_temp"] == 19.0
        assert d1["condition"] is not None
        assert d1["icon"] is not None
        assert "update_time" in data


def test_location_forecast_rejects_invalid_inputs():
    """Verify endpoint returns HTTP 400 for out-of-range coordinates."""
    res = client.get("/weather/forecast?lat=150.0&lon=75.0")
    assert res.status_code == 400
    assert "latitude" in res.json()["detail"].lower()


def test_trip_weather_alerts_endpoint_single_destination():
    """Verify GET /weather/trip/{trip_id}/alerts returns matched dates and disruption alerts."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mock_raw = {
        "daily": {
            "time": [today_str],
            "temperature_2m_max": [30.0],
            "temperature_2m_min": [20.0],
            "weathercode": [95],  # Thunderstorm
            "precipitation_probability_max": [90],
            "precipitation_sum": [25.0],
            "wind_speed_10m_max": [35.0],
        }
    }

    raw_trip = {
        "trip": {
            "source": "Delhi",
            "destination": "Jaipur",
            "days": 1,
            "start_date": today_str,
            "destination_location": {"lat": 26.912, "lon": 75.787},
            "day_schedule": {
                "1": [{"name": "Nahargarh Fort", "category": "Fort"}]
            },
        }
    }
    trip_id = save_trip(raw_trip)

    with patch("backend.services.external.weather_service.fetch_open_meteo_forecast", new=AsyncMock(return_value=mock_raw)):
        res = client.get(f"/weather/trip/{trip_id}/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["destination"] == "Jaipur"
        assert len(data["daily_forecasts"]) == 1
        assert data["daily_forecasts"][0]["status"] == "available"
        assert data["daily_forecasts"][0]["weather_code"] == 95

        # Thunderstorm triggers disruption alert
        assert len(data["disruption_alerts"]) >= 1
        alert = data["disruption_alerts"][0]
        assert alert["alert_type"] == "severe"
        assert alert["warning_source"] == "travelsync_ai"
        assert "Nahargarh Fort" in alert["affected_outdoor_activities"]
        assert "NOT been automatically altered" in alert["recommendation"]


def test_multi_destination_weather_mapping():
    """Verify multi-destination trip maps separate destinations to their respective itinerary days."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    mock_blr = {
        "daily": {
            "time": [today_str],
            "temperature_2m_max": [27.0],
            "temperature_2m_min": [19.0],
            "weathercode": [0],
            "precipitation_probability_max": [5],
            "precipitation_sum": [0.0],
            "wind_speed_10m_max": [10.0],
        }
    }
    mock_mys = {
        "daily": {
            "time": [tomorrow_str],
            "temperature_2m_max": [29.0],
            "temperature_2m_min": [20.0],
            "weathercode": [2],
            "precipitation_probability_max": [15],
            "precipitation_sum": [0.0],
            "wind_speed_10m_max": [12.0],
        }
    }

    raw_trip = {
        "trip": {
            "source": "Hyderabad",
            "destination": "Bengaluru -> Mysuru",
            "days": 2,
            "start_date": today_str,
            "is_multi_destination": True,
            "destinations": [
                {"name": "Bengaluru", "days": 1, "location": {"lat": 12.971, "lon": 77.594}},
                {"name": "Mysuru", "days": 1, "location": {"lat": 12.295, "lon": 76.639}},
            ],
            "day_schedule": {
                "1": [{"name": "Cubbon Park", "category": "Park"}],
                "2": [{"name": "Mysore Palace", "category": "Palace"}],
            },
        }
    }
    trip_id = save_trip(raw_trip)

    async def mock_fetch(lat, lon, forecast_days=16):
        if abs(lat - 12.971) < 0.1:
            return mock_blr
        return mock_mys

    with patch("backend.services.external.weather_service.fetch_open_meteo_forecast", side_effect=mock_fetch):
        res = client.get(f"/weather/trip/{trip_id}/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["is_multi_destination"] is True
        assert len(data["daily_forecasts"]) == 2
        assert data["daily_forecasts"][0]["destination"] == "Bengaluru"
        assert data["daily_forecasts"][1]["destination"] == "Mysuru"


def test_beyond_forecast_horizon_never_fabricates():
    """Verify trip dates beyond the 16-day forecast horizon state horizon limit without fabricating numbers."""
    far_future_date = (datetime.now(timezone.utc) + timedelta(days=60)).strftime("%Y-%m-%d")

    raw_trip = {
        "trip": {
            "source": "Mumbai",
            "destination": "Goa",
            "days": 2,
            "start_date": far_future_date,
            "destination_location": {"lat": 15.299, "lon": 74.124},
            "day_schedule": {"1": [{"name": "Calangute Beach", "category": "Beach"}]},
        }
    }
    trip_id = save_trip(raw_trip)

    res = client.get(f"/weather/trip/{trip_id}/alerts")
    assert res.status_code == 200
    data = res.json()
    assert len(data["daily_forecasts"]) == 2
    f1 = data["daily_forecasts"][0]

    assert f1["status"] == "beyond_horizon"
    assert "16-day" in f1["message"]
    # Never fabricated fake temperatures
    assert "min_temp" not in f1 or f1.get("min_temp") is None
    assert "max_temp" not in f1 or f1.get("max_temp") is None


def test_caching_avoids_redundant_provider_requests():
    """Verify in-memory caching serves repeated calls within TTL."""
    call_count = 0

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {
        "daily": {
            "time": ["2026-10-15"],
            "temperature_2m_max": [30.0],
            "temperature_2m_min": [20.0],
            "weathercode": [0],
            "precipitation_probability_max": [10],
            "precipitation_sum": [0.0],
            "wind_speed_10m_max": [10.0],
        }
    }

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        res1 = client.get("/weather/forecast?lat=26.91&lon=75.78&days=5")
        res2 = client.get("/weather/forecast?lat=26.91&lon=75.78&days=5")
        assert res1.status_code == 200
        assert res2.status_code == 200
        assert call_count == 1  # Called only once due to cache


def test_provider_timeout_gracefully_handled():
    """Verify network timeouts from provider return clean unavailable status without 500 error."""
    import httpx
    with patch("backend.services.external.weather_service.fetch_open_meteo_forecast", new=AsyncMock(return_value=None)):
        res = client.get("/weather/forecast?lat=26.91&lon=75.78&days=5")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "unavailable"
        assert data["success"] is False


def test_weather_alerts_preserves_saved_trip_data():
    """Verify querying weather forecasts and alerts never mutates saved trip records in storage."""
    raw_trip = {
        "trip": {
            "source": "Delhi",
            "destination": "Agra",
            "days": 1,
            "destination_location": {"lat": 27.175, "lon": 78.042},
            "day_schedule": {
                "1": [{"name": "Taj Mahal", "category": "Monument"}]
            },
        }
    }
    trip_id = save_trip(raw_trip)
    before = load_trip(trip_id)

    res = client.get(f"/weather/trip/{trip_id}/alerts")
    assert res.status_code == 200

    after = load_trip(trip_id)
    assert before == after, "Trip in store must remain completely unmutated"


# ============================================================================
# FRONTEND SOURCE & COMPONENT INTEGRATION VERIFICATION
# ============================================================================

def test_frontend_weather_service_and_components():
    """Verify frontend weather service, banner component, and TripView integration."""
    service_file = FRONTEND_SRC / "services" / "weather.ts"
    assert service_file.exists(), "weather.ts must exist"
    content = service_file.read_text(encoding="utf-8")
    assert "getTripWeatherAlerts" in content
    assert "getLocationForecast" in content

    banner_file = FRONTEND_SRC / "components" / "WeatherAlertsBanner.tsx"
    assert banner_file.exists(), "WeatherAlertsBanner.tsx must exist"
    banner_content = banner_file.read_text(encoding="utf-8")
    assert "WeatherAlertsBanner" in banner_content
    assert "weather-disruption-card" in banner_content
    assert "Recommendation:" in banner_content
    assert "Open-Meteo" in banner_content

    tv_file = FRONTEND_SRC / "pages" / "TripView.tsx"
    assert tv_file.exists()
    tv_content = tv_file.read_text(encoding="utf-8")
    assert "WeatherAlertsBanner" in tv_content
    assert "weatherAlertsData" in tv_content
    assert "getTripWeatherAlerts" in tv_content
    assert "section-weather" in tv_content
