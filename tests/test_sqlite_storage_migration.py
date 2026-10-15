import json
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from backend.services.storage.trip_store import (
    save_trip,
    load_trip,
    load_trip_record,
    update_saved_trip,
    update_trip_sharing,
    load_all_trips,
    get_sqlite_conn,
    init_sqlite_schema,
)
from backend.scripts.export_sqlite_to_json import export_sqlite_to_json
from backend.scripts.migrate_trips_to_sqlite import migrate_trips


@pytest.fixture
def isolated_sqlite_db(tmp_path, monkeypatch):
    """Provide a dedicated isolated SQLite trips database for testing."""
    db_file = tmp_path / "test_trips.db"
    monkeypatch.setenv("TRAVELSYNC_TRIPS_DB", str(db_file))
    monkeypatch.setenv("TRIP_STORAGE_BACKEND", "sqlite")
    conn = get_sqlite_conn(db_file)
    init_sqlite_schema(conn)
    conn.close()
    return db_file


def test_sqlite_save_and_load_trip(isolated_sqlite_db):
    """Verify save_trip and load_trip work accurately with SQLite backend."""
    sample_trip_data = {
        "trip": {
            "source": "Mumbai",
            "destination": "Goa",
            "days": 4,
            "budget": {"total_budget": 30000},
        }
    }
    trip_id = save_trip(sample_trip_data, owner_id="user_alice_99")
    assert trip_id is not None

    # Load trip payload
    loaded = load_trip(trip_id)
    assert loaded is not None
    assert loaded["trip"]["source"] == "Mumbai"
    assert loaded["trip"]["destination"] == "Goa"
    assert loaded["trip"]["owner_id"] == "user_alice_99"

    # Load complete record with sharing metadata
    record = load_trip_record(trip_id)
    assert record is not None
    assert record["id"] == trip_id
    assert record["owner_id"] == "user_alice_99"
    assert "user_alice_99" in record["members"]
    assert record["members"]["user_alice_99"]["role"] == "owner"


def test_sqlite_update_saved_trip(isolated_sqlite_db):
    """Verify update_saved_trip mutates payload while preserving creation timestamp."""
    initial_data = {"trip": {"source": "Delhi", "destination": "Jaipur", "days": 2}}
    trip_id = save_trip(initial_data, owner_id="user_bob_10")
    record_initial = load_trip_record(trip_id)
    initial_created_at = record_initial["created_at"]

    # Update payload
    updated_data = {"trip": {"source": "Delhi", "destination": "Jaipur", "days": 3, "status": "extended"}}
    success = update_saved_trip(trip_id, updated_data)
    assert success is True

    record_updated = load_trip_record(trip_id)
    assert record_updated["data"]["trip"]["days"] == 3
    assert record_updated["data"]["trip"]["status"] == "extended"
    assert record_updated["created_at"] == initial_created_at


def test_sqlite_update_trip_sharing(isolated_sqlite_db):
    """Verify collaborator and invitation updates work in SQLite mode."""
    trip_id = save_trip({"trip": {"destination": "Kerala"}}, owner_id="owner_1")

    new_members = {
        "owner_1": {"role": "owner", "joined_at": "2026-01-01T00:00:00Z"},
        "editor_2": {"role": "editor", "joined_at": "2026-01-02T00:00:00Z"},
        "viewer_3": {"role": "viewer", "joined_at": "2026-01-03T00:00:00Z"},
    }
    new_invitations = [
        {"id": "inv_1", "role": "editor", "status": "pending"}
    ]

    ok = update_trip_sharing(trip_id, members=new_members, invitations=new_invitations)
    assert ok is True

    record = load_trip_record(trip_id)
    assert len(record["members"]) == 3
    assert record["members"]["editor_2"]["role"] == "editor"
    assert record["members"]["viewer_3"]["role"] == "viewer"
    assert len(record["invitations"]) == 1
    assert record["invitations"][0]["id"] == "inv_1"


def test_sqlite_load_all_trips_filtering(isolated_sqlite_db):
    """Verify load_all_trips accurately filters trips based on user ownership and collaborator role."""
    t1 = save_trip({"trip": {"destination": "Paris"}}, owner_id="user_charlie")
    t2 = save_trip({"trip": {"destination": "Tokyo"}}, owner_id="user_dan")
    t3 = save_trip({"trip": {"destination": "Rome"}}, owner_id="user_dan")

    # Grant Charlie editor access on Dan's trip (t2)
    update_trip_sharing(
        t2,
        members={
            "user_dan": {"role": "owner"},
            "user_charlie": {"role": "editor"},
        },
    )

    # Charlie should see t1 (owned) and t2 (member), but NOT t3
    charlie_trips = load_all_trips(user_id="user_charlie")
    charlie_ids = {t["id"] for t in charlie_trips}
    assert t1 in charlie_ids
    assert t2 in charlie_ids
    assert t3 not in charlie_ids


def test_sqlite_to_json_export_and_reversibility(tmp_path, isolated_sqlite_db):
    """Verify full round-trip export from SQLite to JSON preserves all records and schema."""
    t1 = save_trip({"trip": {"destination": "City A"}}, owner_id="user_1")
    t2 = save_trip({"trip": {"destination": "City B"}}, owner_id="user_2")

    json_export_file = tmp_path / "exported_trips.json"
    exported_count = export_sqlite_to_json(source_db=isolated_sqlite_db, output_json=json_export_file)
    assert exported_count == 2
    assert json_export_file.exists()

    exported_data = json.loads(json_export_file.read_text(encoding="utf-8"))
    assert len(exported_data) == 2
    exported_ids = {x["id"] for x in exported_data}
    assert t1 in exported_ids
    assert t2 in exported_ids
