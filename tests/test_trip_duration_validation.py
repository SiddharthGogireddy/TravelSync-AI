import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from backend.app import app
from backend.models.trip import TripRequest
from backend.services.planner.trip_optimizer import optimize_trip

client = TestClient(app)

SAMPLE_REQUEST_PAYLOAD = {
    "source": "Bengaluru",
    "destination": "Mysuru",
    "travel_mode": "car",
    "travelers": [
        {
            "name": "Alex",
            "interests": ["Historic", "Palaces"],
            "budget": "Medium",
            "pace": "Balanced",
        }
    ],
    "mandatory_visits": [],
}


def test_planner_days_zero_returns_422():
    """Verify that days=0 produces an HTTP 422 client error and never triggers HTTP 500 ZeroDivisionError."""
    payload = {**SAMPLE_REQUEST_PAYLOAD, "days": 0}
    response = client.post("/planner/", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Pydantic v2 reports ge constraint failure in detail
    assert any("greater than or equal to 1" in str(err) for err in data["detail"])


def test_planner_negative_days_returns_422():
    """Verify that negative days produces an HTTP 422 error."""
    payload = {**SAMPLE_REQUEST_PAYLOAD, "days": -5}
    response = client.post("/planner/", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("greater than or equal to 1" in str(err) for err in data["detail"])


def test_planner_days_above_max_returns_422():
    """Verify that days > 30 produces an HTTP 422 error."""
    payload = {**SAMPLE_REQUEST_PAYLOAD, "days": 31}
    response = client.post("/planner/", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("less than or equal to 30" in str(err) for err in data["detail"])


def test_trip_request_schema_boundary_validation():
    """Verify TripRequest model enforces 1 <= days <= 30 directly."""
    # days = 1 (valid boundary)
    req_1 = TripRequest(**{**SAMPLE_REQUEST_PAYLOAD, "days": 1})
    assert req_1.days == 1

    # days = 30 (valid boundary)
    req_30 = TripRequest(**{**SAMPLE_REQUEST_PAYLOAD, "days": 30})
    assert req_30.days == 30

    # days = 0 (invalid)
    with pytest.raises(ValidationError):
        TripRequest(**{**SAMPLE_REQUEST_PAYLOAD, "days": 0})

    # days = -1 (invalid)
    with pytest.raises(ValidationError):
        TripRequest(**{**SAMPLE_REQUEST_PAYLOAD, "days": -1})

    # days = 31 (invalid)
    with pytest.raises(ValidationError):
        TripRequest(**{**SAMPLE_REQUEST_PAYLOAD, "days": 31})


def test_direct_optimizer_calls_with_invalid_durations():
    """Verify optimizer defensively rejects invalid durations with ValueError instead of dividing by zero."""
    dummy_places = [
        {"name": "Place A", "score": 8, "lat": 12.0, "lon": 77.0, "matched_interests": ["Historic"]},
        {"name": "Place B", "score": 9, "lat": 12.1, "lon": 77.1, "matched_interests": ["Historic"]},
    ]

    # days = 0
    with pytest.raises(ValueError) as exc:
        optimize_trip(dummy_places, days=0)
    assert "must be an integer >= 1" in str(exc.value)

    # days = -3
    with pytest.raises(ValueError) as exc:
        optimize_trip(dummy_places, days=-3)
    assert "must be an integer >= 1" in str(exc.value)

    # days = non-integer
    with pytest.raises(ValueError) as exc:
        optimize_trip(dummy_places, days="two")  # type: ignore
    assert "must be an integer >= 1" in str(exc.value)


def test_direct_optimizer_valid_one_day():
    """Verify optimizer functions properly with a valid 1-day itinerary."""
    dummy_places = [
        {"name": "Place A", "score": 8, "lat": 12.0, "lon": 77.0, "matched_interests": ["Historic"]},
    ]
    schedule = optimize_trip(dummy_places, days=1)
    assert "1" in schedule
    assert len(schedule) == 1
    assert schedule["1"][0]["name"] == "Place A"
