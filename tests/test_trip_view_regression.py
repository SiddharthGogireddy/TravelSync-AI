import pytest
from starlette.testclient import TestClient
from backend.app import app
from backend.services.storage.trip_store import save_trip

client = TestClient(app)

def test_trip_view_api_regression_handling(isolated_storage):
    """Verify that GET /trip/{trip_id} and GET /expense/{trip_id} handle standard, legacy, and malformed trips safely."""
    # 1. Full standard trip
    full_id = save_trip({
        "trip": {
            "source": "Bengaluru",
            "destination": "Goa",
            "days": 3,
            "destination_location": {"lat": 15.2993, "lon": 74.1240},
            "weather": [{"date": "2026-10-10", "max_temp": 30, "min_temp": 24, "description": "Sunny"}],
            "hotels": [{"name": "Goa Beach Resort", "lat": 15.29, "lon": 74.12, "distance_km": 1.2}],
            "places": [{"name": "Calangute Beach", "lat": 15.54, "lon": 73.75, "category": "Beach", "distance_km": 0.5}],
            "travelers": [{"name": "Alice", "budget": "5000", "interests": ["Beach"], "pace": "Balanced"}],
            "budget": {
                "total_budget": 15000,
                "estimated_cost": 12000,
                "remaining": 3000,
                "status": "Within Budget",
                "categories": {"hotel": 5000, "food": 3000, "transport": 2000, "activities": 1000, "emergency": 1000}
            },
            "day_schedule": {"1": [{"name": "Calangute Beach"}]},
            "route_coordinates": [[15.29, 74.12], [15.54, 73.75]]
        }
    })

    # 2. Minimal legacy Coorg trip (no weather, no hotels, no travelers, invalid lat/lon string)
    coorg_id = save_trip({
        "trip": {
            "destination": "Coorg",
            "destination_location": {"lat": "not_a_number", "lon": "invalid"}
        }
    })

    # 3. Legacy Ooty trip (None destination_location, no weather)
    ooty_id = save_trip({
        "trip": {
            "destination": "Ooty",
            "destination_location": None
        }
    })

    # 4. Unwrapped trip (flat dictionary without 'trip' wrapper)
    unwrapped_id = save_trip({
        "destination": "Mysuru",
        "source": "Bengaluru",
        "days": 2
    })

    for tid, expected_dest in [(full_id, "Goa"), (coorg_id, "Coorg"), (ooty_id, "Ooty"), (unwrapped_id, "Mysuru")]:
        # Test GET /trip/{trip_id}
        res = client.get(f"/trip/{tid}")
        assert res.status_code == 200, f"GET /trip/{tid} failed: {res.text}"
        data = res.json()
        assert "trip" in data
        assert "dashboard" in data
        trip = data["trip"]
        assert trip["destination"] == expected_dest
        # Critical regressions: weather, hotels, places, travelers, day_schedule MUST be safe arrays/dicts
        assert isinstance(trip["weather"], list)
        assert isinstance(trip["hotels"], list)
        assert isinstance(trip["places"], list)
        assert isinstance(trip["travelers"], list)
        assert isinstance(trip["day_schedule"], dict)
        assert isinstance(trip["route_coordinates"], list)
        assert isinstance(trip["budget"], dict)
        assert isinstance(data["dashboard"], dict)

        # Test GET /expense/{trip_id} - previously crashed with KeyError: 'travelers' or ZeroDivisionError
        exp_res = client.get(f"/expense/{tid}")
        assert exp_res.status_code == 200, f"GET /expense/{tid} failed: {exp_res.text}"
        exp_data = exp_res.json()
        assert "total_budget" in exp_data or "expenses" in exp_data
