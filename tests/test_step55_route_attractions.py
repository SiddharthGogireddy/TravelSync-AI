import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.app import app
from backend.services.planner.route_attractions import (
    sample_corridor_waypoints,
    calculate_detour_impact,
    discover_route_attractions,
    insert_route_stop_into_day,
)
from backend.services.storage.trip_store import save_trip

client = TestClient(app)

def test_corridor_sampling_and_detour_calculation():
    print("Testing corridor sampling and detour calculation...")
    coords = [
        [78.4867, 17.3850],  # Hyderabad
        [77.5946, 12.9716],  # Bengaluru
        [76.6394, 12.2958],  # Mysuru
    ]
    waypoints = sample_corridor_waypoints(coords, num_samples=3)
    assert len(waypoints) == 3
    for wp in waypoints:
        assert "lat" in wp and "lon" in wp and "percent" in wp
        assert 0 < wp["percent"] < 100

    impact = calculate_detour_impact(
        waypoint_lat=17.0,
        waypoint_lon=78.0,
        attraction_lat=17.05,
        attraction_lon=78.05,
        travel_mode="car",
    )
    assert impact["one_way_km"] > 0
    assert impact["round_trip_detour_km"] > impact["one_way_km"]
    assert impact["added_transit_minutes"] >= 10
    print("Corridor sampling and detour OK!")


def test_discover_route_attractions_sync():
    print("Testing discover_route_attractions...")
    route_obj = {
        "routes": [
            {
                "geometry": {
                    "coordinates": [
                        [78.4867, 17.3850],
                        [77.9000, 15.5000],
                        [77.5946, 12.9716],
                    ]
                }
            }
        ]
    }
    discovered = asyncio.run(discover_route_attractions(
        route=route_obj,
        destination_places=[],
        travel_mode="car",
        max_detour_km=25.0,
    ))
    assert len(discovered) > 0
    for stop in discovered:
        assert stop["is_route_stop"] is True
        assert stop["detour_distance_km"] <= 25.0
        assert "corridor_progress_percent" in stop
        assert "added_travel_time_minutes" in stop
        assert "recommended_pause_minutes" in stop
    print(f"Discovered {len(discovered)} corridor attractions successfully!")


def test_insert_route_stop_into_day():
    print("Testing insert_route_stop_into_day...")
    sample_trip = {
        "destination": "Bengaluru",
        "day_schedule": {
            "1": [
                {"name": "Cubbon Park", "travel_time_minutes": 20},
                {"name": "Lalbagh", "travel_time_minutes": 25},
            ]
        }
    }
    stop_to_add = {
        "id": "stop_lepakshi",
        "name": "Lepakshi Temple Complex",
        "category": "Historical Heritage",
        "lat": 13.80,
        "lon": 77.60,
        "detour_distance_km": 8.5,
        "added_travel_time_minutes": 25,
        "recommended_pause_minutes": 45,
        "score": 9,
    }

    updated, audit = insert_route_stop_into_day(
        trip_data=sample_trip,
        day_number=1,
        route_stop=stop_to_add,
    )
    assert audit["success"] is True
    assert audit["inserted_stop"] == "Lepakshi Temple Complex"
    assert audit["added_detour_km"] == 8.5
    assert len(updated["day_schedule"]["1"]) == 3
    assert updated["day_schedule"]["1"][1]["name"] == "Lepakshi Temple Complex"
    assert updated["day_schedule"]["1"][1]["is_en_route"] is True
    print("Insert route stop into day OK!")


def test_add_route_stop_api():
    print("Testing add route stop API endpoint...")
    trip_payload = {
        "destination": "Goa",
        "day_schedule": {
            "1": [
                {"name": "Calangute", "travel_time_minutes": 15},
                {"name": "Baga", "travel_time_minutes": 10},
            ]
        },
        "route_attractions": [
            {
                "id": "corridor_stop_1",
                "name": "Karnala Bird Sanctuary",
                "category": "Nature & Wildlife",
                "lat": 18.89,
                "lon": 73.11,
                "detour_distance_km": 4.5,
                "added_travel_time_minutes": 18,
                "recommended_pause_minutes": 45,
            }
        ]
    }
    test_id = save_trip({"trip": trip_payload})

    res = client.post(
        f"/trip/{test_id}/add-route-stop",
        json={
            "day": 1,
            "route_stop": trip_payload["route_attractions"][0],
        }
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["audit"]["inserted_stop"] == "Karnala Bird Sanctuary"
    places_day1 = body["trip"]["day_schedule"]["1"]
    assert any(p["name"] == "Karnala Bird Sanctuary" for p in places_day1)
    print("Step 55 test complete and ALL PASSED!")


if __name__ == "__main__":
    test_corridor_sampling_and_detour_calculation()
    test_discover_route_attractions_sync()
    test_insert_route_stop_into_day()
    test_add_route_stop_api()
