import json
import pytest
from fastapi.testclient import TestClient

import backend.services.storage.rating_store as rating_store
import backend.services.storage.template_store as template_store
import backend.services.storage.trip_store as trip_store
from backend.services.storage.rating_store import (
    load_ratings,
    save_ratings,
    get_rating,
    save_rating,
    StorageCorruptedError as RatingStorageCorruptedError,
)
from backend.services.storage.template_store import (
    load_all_templates,
    get_template,
    save_template_from_trip,
    create_trip_from_template,
    delete_template,
    StorageCorruptedError as TemplateStorageCorruptedError,
)
from backend.app import app

client = TestClient(app)


# ============================================================================
# RATING STORE TESTS
# ============================================================================

def test_ratings_valid_existing_loads_and_crud_normally(tmp_path, monkeypatch):
    """Verify valid rating storage loads correctly and handles save/get while preserving data."""
    store_file = tmp_path / "trip_ratings.json"
    initial_data = {
        "trip-1": {"rating": 5, "feedback": "Amazing experience!"},
        "trip-2": {"rating": 4, "feedback": "Very good"},
    }
    store_file.write_text(json.dumps(initial_data, indent=4), encoding="utf-8")
    monkeypatch.setattr(rating_store, "FILE", store_file)

    loaded = load_ratings()
    assert loaded == initial_data
    assert get_rating("trip-1") == {"rating": 5, "feedback": "Amazing experience!"}
    assert get_rating("trip-nonexistent") is None

    # Save a rating for a new trip
    res1 = save_rating("trip-3", 5, "Perfect trip")
    assert res1 == {"rating": 5, "feedback": "Perfect trip"}
    assert get_rating("trip-3") == {"rating": 5, "feedback": "Perfect trip"}
    # Existing ratings are preserved
    assert get_rating("trip-1") == {"rating": 5, "feedback": "Amazing experience!"}
    assert get_rating("trip-2") == {"rating": 4, "feedback": "Very good"}

    # Update an existing rating
    res2 = save_rating("trip-2", 5, "Updated feedback")
    assert res2 == {"rating": 5, "feedback": "Updated feedback"}
    assert get_rating("trip-2") == {"rating": 5, "feedback": "Updated feedback"}


def test_ratings_missing_file_initializes_empty_dict(tmp_path, monkeypatch):
    """Verify that a missing trip_ratings file initializes safely as an empty dict."""
    store_file = tmp_path / "missing_ratings.json"
    assert not store_file.exists()
    monkeypatch.setattr(rating_store, "FILE", store_file)

    ratings = load_ratings()
    assert ratings == {}
    assert store_file.exists()
    assert json.loads(store_file.read_text(encoding="utf-8")) == {}


def test_ratings_zero_byte_file_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that a 0-byte rating store file raises RatingStorageCorruptedError."""
    store_file = tmp_path / "zero_ratings.json"
    store_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(rating_store, "FILE", store_file)

    with pytest.raises(RatingStorageCorruptedError) as exc_info:
        load_ratings()
    assert "empty/truncated" in str(exc_info.value)

    with pytest.raises(RatingStorageCorruptedError):
        get_rating("trip-1")


def test_ratings_malformed_json_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that malformed JSON in rating store raises RatingStorageCorruptedError."""
    store_file = tmp_path / "malformed_ratings.json"
    store_file.write_text('{"trip-1": {"rating": 5, "feedback": "incomplete\n', encoding="utf-8")
    monkeypatch.setattr(rating_store, "FILE", store_file)

    with pytest.raises(RatingStorageCorruptedError) as exc_info:
        load_ratings()
    assert "Malformed JSON in" in str(exc_info.value)


def test_ratings_invalid_data_shape_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify non-dict root or non-dict values raise RatingStorageCorruptedError."""
    store_file = tmp_path / "invalid_shape_ratings.json"

    # Non-dict root (e.g. list)
    store_file.write_text('["not", "a", "dict"]', encoding="utf-8")
    monkeypatch.setattr(rating_store, "FILE", store_file)
    with pytest.raises(RatingStorageCorruptedError) as exc_info1:
        load_ratings()
    assert "expected dict" in str(exc_info1.value)

    # Dict root with non-dict value
    store_file.write_text('{"trip-1": "should be a dict"}', encoding="utf-8")
    with pytest.raises(RatingStorageCorruptedError) as exc_info2:
        load_ratings()
    assert "rating entries must be dicts" in str(exc_info2.value)


def test_ratings_failed_write_on_corrupted_preserves_original_file_bytes(tmp_path, monkeypatch):
    """Verify attempting to save rating on corrupted storage raises error and leaves bytes unchanged."""
    store_file = tmp_path / "corrupted_ratings.json"
    corrupt_bytes = b'{\n  "trip-corrupt": {"rating": UNPARSABLE'
    store_file.write_bytes(corrupt_bytes)
    monkeypatch.setattr(rating_store, "FILE", store_file)

    with pytest.raises(RatingStorageCorruptedError):
        save_rating("trip-1", 5, "Must not corrupt")

    # Assert file bytes are strictly identical
    assert store_file.read_bytes() == corrupt_bytes


# ============================================================================
# TEMPLATE STORE TESTS
# ============================================================================

def test_templates_valid_existing_loads_and_crud_normally(tmp_path, monkeypatch):
    """Verify valid template storage loads correctly and handles create/read/delete."""
    store_file = tmp_path / "templates.json"
    initial_data = [
        {
            "id": "tpl_test1",
            "name": "Weekend in Coorg",
            "description": "Scenic hills getaway",
            "category": "Nature",
            "source_trip_id": "test-baseline-sample-trip-id",
            "created_at": "2026-01-01T00:00:00Z",
            "destination": "Coorg",
            "source": "Bengaluru",
            "duration_days": 2,
            "travel_mode": "car",
            "preferences": ["Coffee Plantations"],
            "budget_summary": {"total_budget": 15000, "estimated_cost": 12000},
            "route_summary": {"distance_km": 250, "duration_hr": 5.5},
            "itinerary_structure": {"days_count": 2, "places_count": 5, "hotels_count": 1},
            "template_data": {
                "trip": {
                    "destination": "Coorg",
                    "source": "Bengaluru",
                    "days": 2,
                    "travel_mode": "car",
                    "budget": {"total_budget": 15000},
                }
            },
        }
    ]
    store_file.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")
    monkeypatch.setattr(template_store, "FILE", store_file)

    loaded = load_all_templates()
    assert len(loaded) == 1
    assert loaded[0]["id"] == "tpl_test1"

    tpl = get_template("tpl_test1")
    assert tpl is not None
    assert tpl["name"] == "Weekend in Coorg"
    assert get_template("tpl_nonexistent") is None

    # Test creating trip from template
    trip_file = tmp_path / "trips.json"
    trip_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(trip_store, "FILE", trip_file)

    new_trip_id, new_trip = create_trip_from_template("tpl_test1", overrides={"budget": 20000})
    assert new_trip_id is not None
    assert new_trip["trip"]["budget"]["total_budget"] == 20000
    # Original template is unaffected
    assert get_template("tpl_test1")["template_data"]["trip"]["budget"]["total_budget"] == 15000

    # Test delete template
    assert delete_template("tpl_test1") is True
    assert load_all_templates() == []
    assert delete_template("tpl_nonexistent") is False


def test_templates_missing_file_initializes_empty_list(tmp_path, monkeypatch):
    """Verify that a missing templates file initializes safely as an empty list."""
    store_file = tmp_path / "missing_templates.json"
    assert not store_file.exists()
    monkeypatch.setattr(template_store, "FILE", store_file)

    templates = load_all_templates()
    assert templates == []
    assert store_file.exists()
    assert json.loads(store_file.read_text(encoding="utf-8")) == []


def test_templates_zero_byte_file_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that a 0-byte template store file raises TemplateStorageCorruptedError."""
    store_file = tmp_path / "zero_templates.json"
    store_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(template_store, "FILE", store_file)

    with pytest.raises(TemplateStorageCorruptedError) as exc_info:
        load_all_templates()
    assert "empty/truncated" in str(exc_info.value)

    with pytest.raises(TemplateStorageCorruptedError):
        get_template("tpl_test1")


def test_templates_malformed_json_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify that malformed JSON in template store raises TemplateStorageCorruptedError."""
    store_file = tmp_path / "malformed_templates.json"
    store_file.write_text('[\n  {"id": "tpl_broken", "name": "incomplete\n', encoding="utf-8")
    monkeypatch.setattr(template_store, "FILE", store_file)

    with pytest.raises(TemplateStorageCorruptedError) as exc_info:
        load_all_templates()
    assert "Malformed JSON in" in str(exc_info.value)


def test_templates_invalid_data_shape_raises_storage_corrupted_error(tmp_path, monkeypatch):
    """Verify non-list root or non-dict items raise TemplateStorageCorruptedError."""
    store_file = tmp_path / "invalid_shape_templates.json"

    # Non-list root (e.g. dict)
    store_file.write_text('{"templates": []}', encoding="utf-8")
    monkeypatch.setattr(template_store, "FILE", store_file)
    with pytest.raises(TemplateStorageCorruptedError) as exc_info1:
        load_all_templates()
    assert "expected list" in str(exc_info1.value)

    # List with non-dict element
    store_file.write_text('["not_a_dict_entry"]', encoding="utf-8")
    with pytest.raises(TemplateStorageCorruptedError) as exc_info2:
        load_all_templates()
    assert "template entries must be dicts" in str(exc_info2.value)


def test_templates_failed_write_on_corrupted_preserves_original_file_bytes(tmp_path, monkeypatch):
    """Verify attempting to save or delete template on corrupted storage raises error and leaves bytes unchanged."""
    store_file = tmp_path / "corrupted_templates.json"
    corrupt_bytes = b'[\n  {"id": "tpl_corrupt", "data": UNPARSABLE'
    store_file.write_bytes(corrupt_bytes)
    monkeypatch.setattr(template_store, "FILE", store_file)

    # Seed a valid source trip in trip store
    trip_file = tmp_path / "trips.json"
    trip_file.write_text(json.dumps([
        {
            "id": "sample-source-trip",
            "created_at": "2026-01-01T00:00:00Z",
            "data": {
                "trip": {
                    "destination": "Ooty",
                    "source": "Coimbatore",
                    "days": 2,
                    "travel_mode": "car",
                }
            }
        }
    ]), encoding="utf-8")
    monkeypatch.setattr(trip_store, "FILE", trip_file)

    # Attempt save_template_from_trip
    with pytest.raises(TemplateStorageCorruptedError):
        save_template_from_trip("sample-source-trip", name="Test Template")

    # Attempt delete_template
    with pytest.raises(TemplateStorageCorruptedError):
        delete_template("any_id")

    # Assert template store file bytes are strictly identical
    assert store_file.read_bytes() == corrupt_bytes


# ============================================================================
# API ENDPOINT BEHAVIOR WITH CORRUPTED STORAGE
# ============================================================================

def test_rating_and_template_api_endpoints_on_corrupted_storage(isolated_storage, tmp_path, monkeypatch):
    """Verify API endpoints handle corrupted rating and template stores safely without modifying files."""
    # Seed a valid trip so trip lookup succeeds
    trip_file = tmp_path / "trips.json"
    sample_trip = {
        "id": "test-trip-id",
        "created_at": "2026-01-01T00:00:00Z",
        "data": {"trip": {"destination": "Mysore"}},
    }
    trip_file.write_text(json.dumps([sample_trip]), encoding="utf-8")
    monkeypatch.setattr(trip_store, "FILE", trip_file)

    # Corrupted rating store
    rating_file = tmp_path / "ratings_corrupted.json"
    rating_corrupt_bytes = b'CORRUPTED_RATING_CONTENT'
    rating_file.write_bytes(rating_corrupt_bytes)
    monkeypatch.setattr(rating_store, "FILE", rating_file)

    # Corrupted template store
    template_file = tmp_path / "templates_corrupted.json"
    template_corrupt_bytes = b'CORRUPTED_TEMPLATE_CONTENT'
    template_file.write_bytes(template_corrupt_bytes)
    monkeypatch.setattr(template_store, "FILE", template_file)

    # Rating endpoints should fail, preserving corrupt bytes
    with pytest.raises(RatingStorageCorruptedError):
        client.get("/trip/test-trip-id/rating")
    with pytest.raises(RatingStorageCorruptedError):
        client.post("/trip/test-trip-id/rating", json={"rating": 5, "feedback": "Great"})
    assert rating_file.read_bytes() == rating_corrupt_bytes

    # Template list endpoint should fail, preserving corrupt bytes
    with pytest.raises(TemplateStorageCorruptedError):
        client.get("/templates")
    assert template_file.read_bytes() == template_corrupt_bytes

    # Template create from trip endpoint should return 500, preserving corrupt bytes
    resp = client.post("/templates/from-trip/test-trip-id", json={"name": "My Template"})
    assert resp.status_code == 500
    assert template_file.read_bytes() == template_corrupt_bytes

    resp2 = client.post("/trip/test-trip-id/template", json={"name": "My Template"})
    assert resp2.status_code == 500
    assert template_file.read_bytes() == template_corrupt_bytes
