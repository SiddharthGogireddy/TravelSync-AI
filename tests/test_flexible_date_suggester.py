"""
Tests for TravelSync AI - Flexible Travel Date Suggestion Engine
Verifies candidate window ranking, live forecast vs provisional seasonal confidence,
weekend preference weighting, validation rules, API endpoints, and regression with exact date planning.
"""

import pytest
from datetime import datetime, timedelta, timezone, date
from fastapi.testclient import TestClient

from backend.app import app
from backend.models.trip import TripRequest, Traveler, SuggestDatesRequest
from backend.services.planner.date_suggester import (
    suggest_travel_dates,
    evaluate_candidate_window,
    pick_diverse_recommendations,
    MONTHLY_CLIMATE_NORMALS,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.anyio
async def test_suggest_travel_dates_success():
    """Verify that date suggester generates valid, ranked candidate windows."""
    result = await suggest_travel_dates(
        destination="Goa",
        days=3,
        flexible_window="next_month",
        weather_preference="avoid_rain",
        prefer_weekends=True,
    )

    assert "Goa" in result["destination"]
    assert result["trip_days"] == 3
    assert "recommendations" in result
    assert len(result["recommendations"]) >= 1

    for rec in result["recommendations"]:
        assert "start_date" in rec
        assert "end_date" in rec
        assert rec["duration_days"] == 3
        assert 0 <= rec["suitability_score"] <= 100
        assert "badge" in rec
        assert "weather_summary" in rec
        assert "avg_max_temp" in rec["weather_summary"]
        assert "rain_probability" in rec["weather_summary"]
        assert rec["confidence"] in ["forecast_verified", "provisional_seasonal"]
        assert isinstance(rec["reasons"], list)
        assert len(rec["reasons"]) > 0

        # Verify date math: duration matches
        d_start = datetime.strptime(rec["start_date"], "%Y-%m-%d").date()
        d_end = datetime.strptime(rec["end_date"], "%Y-%m-%d").date()
        assert (d_end - d_start).days + 1 == 3


@pytest.mark.anyio
async def test_live_forecast_vs_provisional_confidence():
    """Verify distinction between verified 16-day forecast and provisional seasonal estimates."""
    today = datetime.now(timezone.utc).date()

    # 1. Immediate window within 14 days
    res_live = await suggest_travel_dates(
        destination="Bengaluru",
        days=2,
        earliest_date=(today + timedelta(days=2)).strftime("%Y-%m-%d"),
        latest_date=(today + timedelta(days=6)).strftime("%Y-%m-%d"),
    )
    assert len(res_live["recommendations"]) > 0
    top_live = res_live["recommendations"][0]
    assert top_live["confidence"] == "forecast_verified"
    assert "Live Forecast" in top_live["confidence_label"]

    # 2. Window far beyond 16 days (e.g. 40 days out)
    res_provisional = await suggest_travel_dates(
        destination="Bengaluru",
        days=3,
        earliest_date=(today + timedelta(days=40)).strftime("%Y-%m-%d"),
        latest_date=(today + timedelta(days=50)).strftime("%Y-%m-%d"),
    )
    assert len(res_provisional["recommendations"]) > 0
    top_prov = res_provisional["recommendations"][0]
    assert top_prov["confidence"] == "provisional_seasonal"
    assert "Provisional" in top_prov["confidence_label"]
    # Verify trade-offs highlight provisional nature
    assert any("beyond the 16-day" in t.lower() or "verify" in t.lower() for t in top_prov["trade_offs"])


@pytest.mark.anyio
async def test_missing_destination_raises_value_error():
    """Verify that an empty or missing destination raises a ValueError."""
    with pytest.raises(ValueError, match="Destination is required"):
        await suggest_travel_dates(destination="   ")


def test_evaluate_candidate_window_weekend_bonus():
    """Verify that weekend windows receive appropriate weighting."""
    today = date(2026, 10, 15)
    # Friday to Sunday (3 days)
    friday = date(2026, 10, 16)  # Friday
    sunday = date(2026, 10, 18)  # Sunday

    rec_weekend = evaluate_candidate_window(
        cand_start=friday,
        cand_end=sunday,
        trip_days=3,
        today=today,
        live_dates=[],
        live_daily={},
        prefer_weekends=True,
        weather_preference="avoid_rain",
        budget="medium",
        interests=[],
    )
    assert rec_weekend["is_weekend_trip"] is True

    # Monday to Wednesday (3 days)
    monday = date(2026, 10, 19)
    wednesday = date(2026, 10, 21)

    rec_midweek = evaluate_candidate_window(
        cand_start=monday,
        cand_end=wednesday,
        trip_days=3,
        today=today,
        live_dates=[],
        live_daily={},
        prefer_weekends=True,
        weather_preference="avoid_rain",
        budget="medium",
        interests=[],
    )
    assert rec_midweek["is_weekend_trip"] is False
    # With weekend preference, weekend window score is higher than midweek
    assert rec_weekend["suitability_score"] > rec_midweek["suitability_score"]


def test_suggest_dates_api_endpoint(client):
    """Verify POST /planner/suggest-dates returns 200 OK with formatted suggestions."""
    payload = {
        "destination": "Goa",
        "days": 4,
        "flexible_window": "next_month",
        "weather_preference": "avoid_rain",
        "prefer_weekends": True,
    }
    response = client.post("/planner/suggest-dates", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "recommendations" in data["data"]
    assert len(data["data"]["recommendations"]) >= 1


def test_suggest_dates_api_invalid_request(client):
    """Verify POST /planner/suggest-dates validates input duration bounds."""
    payload = {
        "destination": "Goa",
        "days": 0,  # Invalid: must be >= 1
    }
    response = client.post("/planner/suggest-dates", json=payload)
    assert response.status_code == 422


def test_exact_date_trip_planning_regression():
    """Verify that exact-date TripRequest validation remains intact and operational."""
    req = TripRequest(
        source="Bengaluru",
        destination="Mysuru",
        days=3,
        start_date="2026-11-01",
        end_date="2026-11-03",
        travel_mode="car",
        travelers=[
            Traveler(
                name="Siddharth",
                interests=["Heritage"],
                budget="Medium",
                pace="Relaxed",
            )
        ],
    )
    assert req.start_date == "2026-11-01"
    assert req.end_date == "2026-11-03"
    assert req.days == 3
