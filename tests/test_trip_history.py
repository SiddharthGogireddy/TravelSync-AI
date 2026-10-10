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

def test_trip_history_handles_unwrapped_and_malformed_trips(isolated_storage):
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


def test_trip_history_sorting_chronological(isolated_storage):
    """Verify newest generated trips appear at the top, and updates do not change creation order."""
    import time
    from backend.services.storage.trip_store import update_saved_trip

    # 1. Create first trip
    id_first = save_trip({
        "trip": {
            "source": "Bengaluru",
            "destination": "Destination Alpha Chrono",
            "destination_location": {"lat": 12.9716, "lon": 77.5946},
        }
    })

    # Ensure distinct timestamp
    time.sleep(0.01)

    # 2. Create second trip
    id_second = save_trip({
        "trip": {
            "source": "Bengaluru",
            "destination": "Destination Beta Chrono",
            "destination_location": {"lat": 13.0827, "lon": 80.2707},
        }
    })

    # 3. Fetch history and verify second trip appears before first trip
    res = client.get("/trip/history")
    assert res.status_code == 200
    trips = res.json()["trips"]
    ids_in_order = [t["id"] for t in trips]

    assert id_second in ids_in_order
    assert id_first in ids_in_order
    idx_second = ids_in_order.index(id_second)
    idx_first = ids_in_order.index(id_first)
    assert idx_second < idx_first, f"Second trip index ({idx_second}) must be lower (higher in list) than first trip index ({idx_first})"

    # 4. Update the first trip (e.g. simulated edit/replan)
    first_record = load_trip(id_first)
    assert first_record is not None
    first_record["trip"]["notes"] = ["Updated note"]
    update_saved_trip(id_first, first_record)

    # 5. Fetch history again and verify creation order is preserved
    res_after_update = client.get("/trip/history")
    assert res_after_update.status_code == 200
    trips_after = res_after_update.json()["trips"]
    ids_after_order = [t["id"] for t in trips_after]

    idx_second_after = ids_after_order.index(id_second)
    idx_first_after = ids_after_order.index(id_first)
    assert idx_second_after < idx_first_after, "Updating first trip must not move it ahead of second trip"
