import json
import pytest
from fastapi.testclient import TestClient

import backend.services.storage.note_store as note_store
import backend.services.storage.favorite_store as favorite_store
from backend.services.storage.note_store import (
    load_notes,
    save_notes,
    get_notes,
    add_note,
    delete_note,
    StorageCorruptedError as NoteStorageCorruptedError,
)
from backend.services.storage.favorite_store import (
    load_favorites,
    save_favorites,
    add_favorite,
    remove_favorite,
    is_favorite,
    StorageCorruptedError as FavoriteStorageCorruptedError,
)
from backend.app import app

client = TestClient(app)


# ============================================================================
# NOTE STORE TESTS
# ============================================================================

def test_notes_valid_existing_loads_and_crud_normally(tmp_path, monkeypatch):
    """Verify valid note storage loads correctly and handles add/delete while preserving data."""
    store_file = tmp_path / "trip_notes.json"
    initial_data = {
        "trip-1": ["Pack sunscreen", "Check museum tickets"],
        "trip-2": ["Book airport shuttle"],
    }
    store_file.write_text(json.dumps(initial_data, indent=4), encoding="utf-8")
    monkeypatch.setattr(note_store, "FILE", store_file)

    loaded = load_notes()
    assert loaded == initial_data
    assert get_notes("trip-1") == ["Pack sunscreen", "Check museum tickets"]
    assert get_notes("trip-nonexistent") == []

    # Add note to existing trip
    res1 = add_note("trip-1", "Camera charger")
    assert res1 == ["Pack sunscreen", "Check museum tickets", "Camera charger"]
    assert get_notes("trip-1") == ["Pack sunscreen", "Check museum tickets", "Camera charger"]
    assert get_notes("trip-2") == ["Book airport shuttle"]  # preserved

    # Add note to new trip
    res2 = add_note("trip-3", "First note for trip 3")
    assert res2 == ["First note for trip 3"]
    assert get_notes("trip-3") == ["First note for trip 3"]

    # Delete note from trip-1
    assert delete_note("trip-1", 1) is True
    assert get_notes("trip-1") == ["Pack sunscreen", "Camera charger"]
    # Deleting out of bounds returns False
    assert delete_note("trip-1", 99) is False
    assert delete_note("nonexistent", 0) is False


def test_notes_missing_file_initializes_empty_dict(tmp_path, monkeypatch):
    """Verify that a missing trip_notes file initializes safely as an empty dict."""
    store_file = tmp_path / "missing_notes.json"
    assert not store_file.exists()
    monkeypatch.setattr(note_store, "FILE", store_file)

    notes = load_notes()
    assert notes == {}
    assert store_file.exists()
    assert json.loads(store_file.read_text(encoding="utf-8")) == {}


def test_notes_zero_byte_file_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that a 0-byte note store file raises NoteStorageCorruptedError."""
    store_file = tmp_path / "zero_notes.json"
    store_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(note_store, "FILE", store_file)

    with pytest.raises(NoteStorageCorruptedError) as exc_info:
        load_notes()
    assert "empty/truncated" in str(exc_info.value)

    with pytest.raises(NoteStorageCorruptedError):
        get_notes("trip-1")


def test_notes_malformed_json_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that malformed JSON in note store raises NoteStorageCorruptedError."""
    store_file = tmp_path / "malformed_notes.json"
    store_file.write_text('{"trip-1": ["incomplete string\n', encoding="utf-8")
    monkeypatch.setattr(note_store, "FILE", store_file)

    with pytest.raises(NoteStorageCorruptedError) as exc_info:
        load_notes()
    assert "Malformed JSON in" in str(exc_info.value)


def test_notes_invalid_data_shape_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify non-dict root or non-list values raise NoteStorageCorruptedError."""
    store_file = tmp_path / "invalid_shape_notes.json"

    # Non-dict root (e.g. list)
    store_file.write_text('["not", "a", "dict"]', encoding="utf-8")
    monkeypatch.setattr(note_store, "FILE", store_file)
    with pytest.raises(NoteStorageCorruptedError) as exc_info1:
        load_notes()
    assert "expected dict" in str(exc_info1.value)

    # Dict root with non-list value
    store_file.write_text('{"trip-1": "should be a list of strings"}', encoding="utf-8")
    with pytest.raises(NoteStorageCorruptedError) as exc_info2:
        load_notes()
    assert "note entries must be lists" in str(exc_info2.value)


def test_notes_failed_write_on_corrupted_preserves_original_file_bytes(tmp_path, monkeypatch):
    """Verify attempting to add/delete note on corrupted storage raises error and leaves bytes unchanged."""
    store_file = tmp_path / "corrupted_notes.json"
    corrupt_bytes = b'{\n  "trip-corrupt": [UNCLOSED_ARRAY'
    store_file.write_bytes(corrupt_bytes)
    monkeypatch.setattr(note_store, "FILE", store_file)

    # Attempt add_note
    with pytest.raises(NoteStorageCorruptedError):
        add_note("trip-1", "This note must not be saved")

    # Attempt delete_note
    with pytest.raises(NoteStorageCorruptedError):
        delete_note("trip-corrupt", 0)

    # Assert file bytes are strictly identical
    assert store_file.read_bytes() == corrupt_bytes


# ============================================================================
# FAVORITE STORE TESTS
# ============================================================================

def test_favorites_valid_existing_loads_and_crud_normally(tmp_path, monkeypatch):
    """Verify valid favorite storage loads correctly and handles add/remove while preserving data."""
    store_file = tmp_path / "favorites.json"
    initial_data = {
        "favorite_trip_ids": ["trip-1", "trip-2"]
    }
    store_file.write_text(json.dumps(initial_data, indent=4), encoding="utf-8")
    monkeypatch.setattr(favorite_store, "FILE", store_file)

    loaded = load_favorites()
    assert loaded == ["trip-1", "trip-2"]
    assert is_favorite("trip-1") is True
    assert is_favorite("trip-2") is True
    assert is_favorite("trip-3") is False

    # Add favorite
    add_favorite("trip-3")
    assert is_favorite("trip-3") is True
    assert load_favorites() == ["trip-1", "trip-2", "trip-3"]

    # Re-adding already favored trip does not duplicate
    add_favorite("trip-3")
    assert load_favorites() == ["trip-1", "trip-2", "trip-3"]

    # Remove favorite
    remove_favorite("trip-1")
    assert is_favorite("trip-1") is False
    assert load_favorites() == ["trip-2", "trip-3"]

    # Removing non-existent favorite is safe
    remove_favorite("trip-nonexistent")
    assert load_favorites() == ["trip-2", "trip-3"]


def test_favorites_missing_file_initializes_empty_list(tmp_path, monkeypatch):
    """Verify that a missing favorites file initializes safely as an empty list."""
    store_file = tmp_path / "missing_fav.json"
    assert not store_file.exists()
    monkeypatch.setattr(favorite_store, "FILE", store_file)

    favs = load_favorites()
    assert favs == []
    assert store_file.exists()
    data = json.loads(store_file.read_text(encoding="utf-8"))
    assert data == {"favorite_trip_ids": []}


def test_favorites_zero_byte_file_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that a 0-byte favorites file raises FavoriteStorageCorruptedError."""
    store_file = tmp_path / "zero_fav.json"
    store_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(favorite_store, "FILE", store_file)

    with pytest.raises(FavoriteStorageCorruptedError) as exc_info:
        load_favorites()
    assert "empty/truncated" in str(exc_info.value)

    with pytest.raises(FavoriteStorageCorruptedError):
        is_favorite("trip-1")


def test_favorites_malformed_json_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that malformed JSON in favorites file raises FavoriteStorageCorruptedError."""
    store_file = tmp_path / "malformed_fav.json"
    store_file.write_text('{"favorite_trip_ids": ["broken\n', encoding="utf-8")
    monkeypatch.setattr(favorite_store, "FILE", store_file)

    with pytest.raises(FavoriteStorageCorruptedError) as exc_info:
        load_favorites()
    assert "Malformed JSON in" in str(exc_info.value)


def test_favorites_invalid_data_shape_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify non-dict root, missing favorite_trip_ids, or non-list favorite_trip_ids raise error."""
    store_file = tmp_path / "invalid_shape_fav.json"

    # Non-dict root (e.g. list of strings)
    store_file.write_text('["trip-1", "trip-2"]', encoding="utf-8")
    monkeypatch.setattr(favorite_store, "FILE", store_file)
    with pytest.raises(FavoriteStorageCorruptedError) as exc_info1:
        load_favorites()
    assert "expected dict" in str(exc_info1.value)

    # Missing 'favorite_trip_ids' key
    store_file.write_text('{"trips": ["trip-1"]}', encoding="utf-8")
    with pytest.raises(FavoriteStorageCorruptedError) as exc_info2:
        load_favorites()
    assert "expected dict containing 'favorite_trip_ids' list" in str(exc_info2.value)

    # 'favorite_trip_ids' is not a list
    store_file.write_text('{"favorite_trip_ids": "trip-1"}', encoding="utf-8")
    with pytest.raises(FavoriteStorageCorruptedError) as exc_info3:
        load_favorites()
    assert "expected dict containing 'favorite_trip_ids' list" in str(exc_info3.value)


def test_favorites_failed_write_on_corrupted_preserves_original_file_bytes(tmp_path, monkeypatch):
    """Verify attempting to add/remove favorite on corrupted storage raises error and leaves bytes unchanged."""
    store_file = tmp_path / "corrupted_fav.json"
    corrupt_bytes = b'{\n  "favorite_trip_ids": [UNCLOSED_ARRAY'
    store_file.write_bytes(corrupt_bytes)
    monkeypatch.setattr(favorite_store, "FILE", store_file)

    # Attempt add_favorite
    with pytest.raises(FavoriteStorageCorruptedError):
        add_favorite("trip-new")

    # Attempt remove_favorite
    with pytest.raises(FavoriteStorageCorruptedError):
        remove_favorite("trip-new")

    # Assert file bytes are strictly identical
    assert store_file.read_bytes() == corrupt_bytes


# ============================================================================
# API ENDPOINT BEHAVIOR WITH CORRUPTED STORAGE
# ============================================================================

def test_api_endpoints_on_corrupted_storage(isolated_storage, tmp_path, monkeypatch):
    """Verify API endpoints return HTTP 500 when storage is corrupted instead of wiping data."""
    # Seed a sample trip so load_trip("test-trip-id") succeeds
    import backend.services.storage.trip_store as trip_store
    trip_file = tmp_path / "trips.json"
    sample_trip = {
        "id": "test-trip-id",
        "created_at": "2026-01-01T00:00:00Z",
        "data": {"trip": {"destination": "Mysore"}},
    }
    trip_file.write_text(json.dumps([sample_trip]), encoding="utf-8")
    monkeypatch.setattr(trip_store, "FILE", trip_file)

    # Set up corrupted note store
    note_file = tmp_path / "notes_corrupted.json"
    note_file.write_bytes(b'CORRUPTED_NOTE_CONTENT')
    monkeypatch.setattr(note_store, "FILE", note_file)

    # Set up corrupted favorite store
    fav_file = tmp_path / "fav_corrupted.json"
    fav_file.write_bytes(b'CORRUPTED_FAV_CONTENT')
    monkeypatch.setattr(favorite_store, "FILE", fav_file)

    # Notes endpoint should fail with 500, preserving file bytes
    with pytest.raises(NoteStorageCorruptedError):
        client.get("/trip/test-trip-id/notes")
    with pytest.raises(NoteStorageCorruptedError):
        client.post("/trip/test-trip-id/notes", json={"note": "New note"})
    assert note_file.read_bytes() == b'CORRUPTED_NOTE_CONTENT'

    # Favorite endpoint should fail with 500, preserving file bytes
    with pytest.raises(FavoriteStorageCorruptedError):
        client.get("/trip/test-trip-id/favorite")
    with pytest.raises(FavoriteStorageCorruptedError):
        client.post("/trip/test-trip-id/favorite")
    assert fav_file.read_bytes() == b'CORRUPTED_FAV_CONTENT'
