import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip

client = TestClient(app)

def test_trip_history_endpoint_structure():
    """Verify that GET /trip/history returns the expected list structure with normalized trips."""
    response = client.get("/trip/history")
    assert response.status_code == 200
    data = response.json()
    assert "trips" in data
    assert isinstance(data["trips"], list)

    for item in data["trips"]:
        assert "id" in item
        assert isinstance(item["id"], str)
        assert "data" in item
        assert isinstance(item["data"], dict)
        assert "trip" in item["data"]
        assert isinstance(item["data"]["trip"], dict)

        dest_loc = item["data"]["trip"].get("destination_location")
        if dest_loc is not None:
            assert isinstance(dest_loc, dict)
            assert "lat" in dest_loc and "lon" in dest_loc
            assert isinstance(dest_loc["lat"], (int, float))
            assert isinstance(dest_loc["lon"], (int, float))

def test_trip_history_handles_unwrapped_and_malformed_trips():
    """Verify that raw/unwrapped trips and trips with missing/malformed destination_location normalize properly."""
    # 1. Standard trip with valid destination_location
    id_valid = save_trip({
        "trip": {
            "source": "Bengaluru",
            "destination": "Mysuru",
            "destination_location": {"lat": 12.2958, "lon": 76.6394},
        }
    })

    # 2. Raw unwrapped trip (no 'trip' wrapper key) with destination name only
    id_unwrapped = save_trip({
        "destination": "Goa",
        "travel_mode": "car",
    })

    # 3. Trip with None destination_location
    id_none_loc = save_trip({
        "trip": {
            "destination": "Ooty",
            "destination_location": None,
        }
    })

    # 4. Trip with malformed destination_location (string lat/lon or missing fields)
    id_malformed_loc = save_trip({
        "trip": {
            "destination": "Coorg",
            "destination_location": {"lat": "not_a_number"},
        }
    })

    # 5. Trip with empty data
    id_empty = save_trip({})

    response = client.get("/trip/history")
    assert response.status_code == 200
    trips_map = {t["id"]: t for t in response.json()["trips"]}

    # Check valid trip
    assert id_valid in trips_map
    valid_trip = trips_map[id_valid]["data"]["trip"]
    assert valid_trip["destination"] == "Mysuru"
    assert valid_trip["destination_location"] == {"lat": 12.2958, "lon": 76.6394}

    # Check unwrapped trip normalized into data.trip
    assert id_unwrapped in trips_map
    unwrapped_trip = trips_map[id_unwrapped]["data"]["trip"]
    assert unwrapped_trip["destination"] == "Goa"
    assert unwrapped_trip["destination_location"] is None

    # Check trip with None location remains None without crashing
    assert id_none_loc in trips_map
    none_loc_trip = trips_map[id_none_loc]["data"]["trip"]
    assert none_loc_trip["destination"] == "Ooty"
    assert none_loc_trip["destination_location"] is None

    # Check malformed location cleaned up to None
    assert id_malformed_loc in trips_map
    malformed_trip = trips_map[id_malformed_loc]["data"]["trip"]
    assert malformed_trip["destination"] == "Coorg"
    assert malformed_trip["destination_location"] is None

    # Check empty trip normalized safely
    assert id_empty in trips_map
    empty_trip = trips_map[id_empty]["data"]["trip"]
    assert isinstance(empty_trip, dict)
    assert empty_trip.get("destination_location") is None
