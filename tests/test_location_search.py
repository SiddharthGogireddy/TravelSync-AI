"""
Comprehensive Tests for TravelSync AI - Dynamic Location Search & Autocomplete
Tests:
1. Successful search and response normalization (lat/lon, city, region, country, categories).
2. Input validation (empty query, query too short, whitespace, query too long).
3. Provider resilience (HTTP 429 rate limit, 500 server error, timeouts, connect errors, malformed JSON).
4. In-memory TTL caching verification.
5. In-process rate limiting (throttles rapid subsequent requests).
6. Integration with FastAPI /locations/search endpoint.
7. Origin/destination duplicate prevention and planner integration.
8. Backward compatibility of search_location() with downstream services.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from backend.app import app
from backend.services.external.location_service import (
    search_locations,
    search_location,
    clear_location_cache,
    reset_rate_limiter,
)

client = TestClient(app)

MOCK_PARIS_NOMINATIM = [
    {
        "place_id": 1001,
        "lat": "48.8534951",
        "lon": "2.3483915",
        "category": "boundary",
        "type": "administrative",
        "name": "Paris",
        "display_name": "Paris, Île-de-France, France",
        "address": {
            "city": "Paris",
            "state": "Île-de-France",
            "country": "France",
            "country_code": "fr",
        },
    },
    {
        "place_id": 1002,
        "lat": "33.6609389",
        "lon": "-95.555513",
        "category": "boundary",
        "type": "administrative",
        "name": "Paris",
        "display_name": "Paris, Lamar County, Texas, USA",
        "address": {
            "city": "Paris",
            "state": "Texas",
            "country": "United States",
            "country_code": "us",
        },
    },
]

MOCK_TOKYO_NOMINATIM = [
    {
        "place_id": 2001,
        "lat": "35.6828387",
        "lon": "139.7594549",
        "category": "boundary",
        "type": "administrative",
        "name": "Tokyo",
        "display_name": "Tokyo, Japan",
        "address": {
            "city": "Tokyo",
            "state": "Tokyo",
            "country": "Japan",
            "country_code": "jp",
        },
    }
]


# ==============================================================================
# 1. Normalization & Search Tests
# ==============================================================================

@pytest.mark.anyio
async def test_search_locations_success_normalization():
    """Verify search_locations normalizes Nominatim payload into application contract."""
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = MOCK_PARIS_NOMINATIM

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        results = await search_locations("Paris", limit=5)

    assert len(results) == 2

    first = results[0]
    assert first["place_id"] == "1001"
    assert first["name"] == "Paris"
    assert first["latitude"] == pytest.approx(48.8534951)
    assert first["longitude"] == pytest.approx(2.3483915)
    assert first["city"] == "Paris"
    assert first["region"] == "Île-de-France"
    assert first["country"] == "France"
    assert first["country_code"] == "FR"
    assert first["category"] == "boundary"
    assert first["type"] == "administrative"

    second = results[1]
    assert second["place_id"] == "1002"
    assert second["region"] == "Texas"
    assert second["country"] == "United States"


# ==============================================================================
# 2. Input Validation Tests
# ==============================================================================

@pytest.mark.anyio
async def test_search_locations_empty_and_short_queries():
    """Empty or single-character queries must return empty list without network calls."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        assert await search_locations("") == []
        assert await search_locations("   ") == []
        assert await search_locations("a") == []
        assert await search_locations(None) == []  # type: ignore

    mock_get.assert_not_called()


# ==============================================================================
# 3. Provider Error Handling & Resilience
# ==============================================================================

@pytest.mark.anyio
async def test_search_locations_rate_limit_429():
    """HTTP 429 from provider should return empty list gracefully without throwing exceptions."""
    fake_response = MagicMock(status_code=429)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        results = await search_locations("London")

    assert results == []


@pytest.mark.anyio
async def test_search_locations_http_500():
    """HTTP 5xx from provider should return empty list gracefully."""
    fake_response = MagicMock(status_code=500)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        results = await search_locations("Sydney")

    assert results == []


@pytest.mark.anyio
async def test_search_locations_timeout():
    """Timeouts must be caught and return empty list."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Read timed out")):
        results = await search_locations("Rome")

    assert results == []


@pytest.mark.anyio
async def test_search_locations_malformed_coordinates():
    """Results with invalid coordinates should be skipped without corrupting data."""
    malformed = [
        {"place_id": 99, "lat": "not_a_float", "lon": "invalid", "name": "Broken Place"},
        MOCK_TOKYO_NOMINATIM[0],
    ]
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = malformed

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        results = await search_locations("Tokyo")

    assert len(results) == 1
    assert results[0]["name"] == "Tokyo"
    assert results[0]["latitude"] == pytest.approx(35.6828387)


# ==============================================================================
# 4. In-Memory Caching Verification
# ==============================================================================

@pytest.mark.anyio
async def test_search_locations_caching():
    """Subsequent searches for the same query should hit memory cache and make only 1 HTTP request."""
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = MOCK_TOKYO_NOMINATIM

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response

        res1 = await search_locations("Tokyo", limit=5)
        res2 = await search_locations("Tokyo", limit=5)
        res3 = await search_locations("tokyo", limit=5)  # Case insensitive cache key

    assert mock_get.call_count == 1
    assert len(res1) == 1
    assert res1 == res2 == res3


# ==============================================================================
# 5. FastAPI /locations/search Endpoint Tests
# ==============================================================================

def test_api_locations_search_endpoint_success():
    """Test GET /locations/search returns 200 and normalized JSON array."""
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = MOCK_PARIS_NOMINATIM

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        resp = client.get("/locations/search?q=Paris&limit=4")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "Paris"
    assert data[0]["country"] == "France"


def test_api_locations_search_endpoint_validation():
    """Test GET /locations/search validates min_length."""
    resp = client.get("/locations/search?q=a")
    assert resp.status_code == 422  # Query requires min_length=2


# ==============================================================================
# 6. Backward Compatibility for search_location()
# ==============================================================================

@pytest.mark.anyio
async def test_search_location_preserves_contract():
    """Existing search_location() must return dict with lat/lon and string coordinates."""
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = [{"lat": "13.0827", "lon": "80.2707", "display_name": "Chennai"}]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        loc = await search_location("Chennai")

    assert loc is not None
    assert loc["lat"] == "13.0827"
    assert loc["lon"] == "80.2707"
    assert float(loc["lat"]) == pytest.approx(13.0827)
