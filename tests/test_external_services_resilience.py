import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from backend.app import app
from backend.services.external.location_service import search_location
from backend.services.external.place_service import get_places, find_place

client = TestClient(app)


# ==============================================================================
# 1. Location Service Resilience Tests
# ==============================================================================

def test_search_location_success():
    """Verify search_location returns location object on HTTP 200."""
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = [{"lat": "12.9716", "lon": "77.5946", "display_name": "Bengaluru"}]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        loc = asyncio.run(search_location("Bengaluru"))

    assert loc is not None
    assert loc["lat"] == "12.9716"
    assert loc["lon"] == "77.5946"


def test_search_location_http_429_rate_limit():
    """Verify search_location gracefully returns None on HTTP 429 without throwing HTTPStatusError."""
    fake_response = MagicMock(status_code=429)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        loc = asyncio.run(search_location("Bengaluru"))

    assert loc is None


def test_search_location_http_500_error():
    """Verify search_location returns None on external 5xx errors."""
    fake_response = MagicMock(status_code=500)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        loc = asyncio.run(search_location("Bengaluru"))

    assert loc is None


def test_search_location_timeout():
    """Verify search_location catches TimeoutException and returns None."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timed out")):
        loc = asyncio.run(search_location("Bengaluru"))

    assert loc is None


def test_search_location_connection_error():
    """Verify search_location catches network / connection errors and returns None."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
        loc = asyncio.run(search_location("Bengaluru"))

    assert loc is None


def test_search_location_malformed_json():
    """Verify search_location handles non-JSON / HTML error bodies safely."""
    fake_response = MagicMock(status_code=200)
    fake_response.json.side_effect = json.JSONDecodeError("Expecting value", "<html>", 0)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        loc = asyncio.run(search_location("Bengaluru"))

    assert loc is None


def test_search_location_empty_or_blank():
    """Verify empty or whitespace strings return None immediately without making network calls."""
    assert asyncio.run(search_location("")) is None
    assert asyncio.run(search_location("   ")) is None
    assert asyncio.run(search_location(None)) is None


# ==============================================================================
# 2. Place Service Resilience Tests
# ==============================================================================

def test_get_places_success():
    """Verify get_places merges and deduplicates attractions and food places."""
    resp_attr = MagicMock(status_code=200)
    resp_attr.json.return_value = [
        {"xid": "1", "name": "Mysore Palace", "kinds": "historic", "dist": 500, "point": {"lat": 12.3, "lon": 76.6}},
    ]
    resp_food = MagicMock(status_code=200)
    resp_food.json.return_value = [
        {"xid": "2", "name": "Mylari Dosa", "kinds": "foods", "dist": 1200, "point": {"lat": 12.31, "lon": 76.61}},
        {"xid": "1", "name": "Mysore Palace", "kinds": "historic", "dist": 500, "point": {"lat": 12.3, "lon": 76.6}},  # duplicate
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [resp_attr, resp_food]
        places = asyncio.run(get_places(12.3, 76.6))

    assert len(places) == 2
    xids = {p["xid"] for p in places}
    assert xids == {"1", "2"}


def test_get_places_http_429_rate_limit():
    """Verify get_places returns empty list on HTTP 429 without throwing."""
    resp_429 = MagicMock(status_code=429)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_429
        places = asyncio.run(get_places(12.3, 76.6))

    assert places == []


def test_get_places_http_401_unauthorized():
    """Verify get_places returns empty list on invalid / missing API key without crashing."""
    resp_401 = MagicMock(status_code=401)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_401
        places = asyncio.run(get_places(12.3, 76.6))

    assert places == []


def test_get_places_timeout_and_connection_error():
    """Verify get_places returns empty list when network timeouts or drops occur."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timed out")):
        places = asyncio.run(get_places(12.3, 76.6))
    assert places == []

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection failed")):
        places = asyncio.run(get_places(12.3, 76.6))
    assert places == []


def test_get_places_partial_failure_degradation():
    """Verify get_places returns attractions even if food endpoint fails."""
    resp_attr = MagicMock(status_code=200)
    resp_attr.json.return_value = [
        {"xid": "100", "name": "Lalbagh", "kinds": "park", "dist": 300, "point": {"lat": 12.95, "lon": 77.58}},
    ]
    resp_food_fail = MagicMock(status_code=500)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [resp_attr, resp_food_fail]
        places = asyncio.run(get_places(12.95, 77.58))

    assert len(places) == 1
    assert places[0]["name"] == "Lalbagh"


def test_find_place_resilience():
    """Verify find_place handles errors and autosuggest fallback safely."""
    resp_suggest = MagicMock(status_code=200)
    resp_suggest.json.return_value = [
        {"name": "Golconda Fort", "point": {"lat": 17.383, "lon": 78.401}},
    ]

    with patch("backend.services.external.place_service.get_places", new_callable=AsyncMock) as mock_gp, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_gp.return_value = []
        mock_get.return_value = resp_suggest
        found = asyncio.run(find_place("Golconda", 17.383, 78.401))

    assert found is not None
    assert found["name"] == "Golconda Fort"


# ==============================================================================
# 3. Planner Integration & Graceful Failure Tests
# ==============================================================================

PLANNER_PAYLOAD = {
    "source": "Bengaluru",
    "destination": "Mysuru",
    "days": 2,
    "travel_mode": "car",
    "travelers": [
        {"name": "Traveler 1", "interests": ["Historic"], "budget": "Medium", "pace": "Balanced"}
    ],
    "mandatory_visits": [],
}


def test_planner_graceful_when_geocoding_provider_unavailable():
    """Verify POST /planner/ returns controlled error (not 500 crash) when Nominatim fails."""
    with patch("backend.services.planner.itinerary.search_location", new_callable=AsyncMock) as mock_search:
        # Provider outage returns None
        mock_search.return_value = None
        response = client.post("/planner/", json=PLANNER_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "Source or destination not found" in data["error"]


def test_planner_graceful_when_place_provider_unavailable():
    """Verify POST /planner/ still produces a valid itinerary structure when place provider is offline."""
    mock_loc = {"lat": 12.9716, "lon": 77.5946}

    with patch("backend.services.planner.itinerary.search_location", new_callable=AsyncMock) as mock_search, \
         patch("backend.services.planner.itinerary.get_places", new_callable=AsyncMock) as mock_places:
        mock_search.return_value = mock_loc
        # OpenTripMap is completely offline/quota exhausted, returns []
        mock_places.return_value = []

        response = client.post("/planner/", json=PLANNER_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert "trip" in data
    assert data["trip"]["destination"] == "Mysuru"
    assert data["trip"]["days"] == 2
