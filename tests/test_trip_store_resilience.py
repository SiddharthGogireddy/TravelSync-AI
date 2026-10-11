import json
import pytest
from backend.services.storage.trip_store import (
    _read_trips,
    save_trip,
    load_trip,
    load_all_trips,
    StorageCorruptedError,
)
import backend.services.storage.trip_store as trip_store


def test_valid_existing_json_loads_normally(tmp_path, monkeypatch):
    """Verify that valid existing JSON storage loads correctly."""
    store_file = tmp_path / "trips.json"
    initial_data = [
        {"id": "trip-1", "data": {"destination": "Paris"}, "created_at": "2026-01-01T00:00:00Z"},
        {"id": "trip-2", "data": {"destination": "Rome"}, "created_at": "2026-01-02T00:00:00Z"},
    ]
    store_file.write_text(json.dumps(initial_data), encoding="utf-8")
    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    trips = _read_trips()
    assert len(trips) == 2
    assert trips[0]["id"] == "trip-1"
    assert load_all_trips() == initial_data
    assert load_trip("trip-2") == {"destination": "Rome"}


def test_genuinely_missing_file_initializes_properly(tmp_path, monkeypatch):
    """Verify that a genuinely missing data file initializes an empty store without errors."""
    store_file = tmp_path / "trips_missing.json"
    assert not store_file.exists()

    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    trips = _read_trips()
    assert trips == []
    assert store_file.exists()
    assert json.loads(store_file.read_text(encoding="utf-8")) == []


def test_malformed_json_produces_controlled_failure(tmp_path, monkeypatch):
    """Verify that malformed JSON raises StorageCorruptedError instead of returning []."""
    store_file = tmp_path / "trips_malformed.json"
    store_file.write_text('[\n  {"id": "trip-partial", "incomplete": true, \n', encoding="utf-8")

    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    with pytest.raises(StorageCorruptedError) as exc_info:
        _read_trips()
    assert "Malformed JSON in" in str(exc_info.value)

    with pytest.raises(StorageCorruptedError):
        load_all_trips()

    with pytest.raises(StorageCorruptedError):
        load_trip("trip-partial")


def test_empty_zero_byte_file_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that an existing 0-byte file raises StorageCorruptedError."""
    store_file = tmp_path / "trips_zero.json"
    store_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    with pytest.raises(StorageCorruptedError) as exc_info:
        _read_trips()
    assert "empty/truncated" in str(exc_info.value)


def test_non_list_shape_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that a JSON object instead of a list raises StorageCorruptedError."""
    store_file = tmp_path / "trips_dict.json"
    store_file.write_text('{"trips": []}', encoding="utf-8")

    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    with pytest.raises(StorageCorruptedError) as exc_info:
        _read_trips()
    assert "expected list, got dict" in str(exc_info.value)


def test_saving_after_malformed_read_does_not_modify_file_bytes(tmp_path, monkeypatch):
    """Verify that attempting to save when storage is corrupted fails safely and leaves existing file bytes unaltered."""
    store_file = tmp_path / "trips_corrupted.json"
    corrupted_content = b'{"corrupted_data_that_must_not_be_overwritten": [1, 2, 3'
    store_file.write_bytes(corrupted_content)

    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    # Attempt save_trip - must raise StorageCorruptedError
    with pytest.raises(StorageCorruptedError):
        save_trip({"destination": "Tokyo", "days": 5})

    # Verify byte-for-byte preservation of the original file
    assert store_file.read_bytes() == corrupted_content


def test_existing_trips_remain_intact_after_normal_save(tmp_path, monkeypatch):
    """Verify that existing historical trips remain intact and append correctly on normal saves."""
    store_file = tmp_path / "trips_normal.json"
    existing_trip = {
        "id": "existing-uuid-1",
        "created_at": "2026-02-10T10:00:00Z",
        "data": {"destination": "Goa", "days": 3},
    }
    store_file.write_text(json.dumps([existing_trip]), encoding="utf-8")

    monkeypatch.setattr(trip_store, "FILE", store_file)
    monkeypatch.setattr(trip_store, "DATA_DIR", tmp_path)

    new_id = save_trip({"destination": "Kerala", "days": 4})

    all_trips = load_all_trips()
    assert len(all_trips) == 2
    assert all_trips[0]["id"] == "existing-uuid-1"
    assert all_trips[0]["data"]["destination"] == "Goa"
    assert all_trips[1]["id"] == new_id
    assert all_trips[1]["data"]["destination"] == "Kerala"
