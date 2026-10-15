import os
import shutil
import sys
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
BACKEND_DATA = BASE_DIR / "backend" / "data"
BACKEND_DATA_BACKUP = BASE_DIR / "backend" / "data_backup"

DATA_FILES = [
    "expenses.json",
    "favorites.json",
    "templates.json",
    "trip_notes.json",
    "trip_ratings.json",
    "trips.json",
]


@pytest.fixture(scope="session", autouse=True)
def preserve_real_data_session():
    """Ensure real user data is backed up once and never overwritten by test sessions."""
    BACKEND_DATA_BACKUP.mkdir(parents=True, exist_ok=True)
    for fname in DATA_FILES:
        src = BACKEND_DATA / fname
        dst = BACKEND_DATA_BACKUP / fname
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)

    yield


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure rate limiter counters are clean between tests."""
    from backend.services.security.rate_limiter import global_limiter
    global_limiter.reset()
    yield
    global_limiter.reset()


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Provide completely isolated storage paths for all tests, protecting live user data."""
    import json
    import backend.services.storage.trip_store as trip_store
    import backend.services.storage.favorite_store as favorite_store
    import backend.services.storage.note_store as note_store
    import backend.services.storage.rating_store as rating_store
    import backend.services.storage.template_store as template_store
    import backend.services.expense.expense_store as expense_store

    trip_file = tmp_path / "trips.json"
    fav_file = tmp_path / "favorites.json"
    note_file = tmp_path / "trip_notes.json"
    rating_file = tmp_path / "trip_ratings.json"
    template_file = tmp_path / "templates.json"
    expense_file = tmp_path / "expenses.json"

    # Seed an isolated sample trip so tests expecting existing trips (e.g. template tests) pass
    sample_trip = {
        "id": "test-baseline-sample-trip-id",
        "created_at": "2026-01-01T12:00:00Z",
        "data": {
            "trip": {
                "destination": "Goa",
                "source": "Bengaluru",
                "days": 3,
                "travel_mode": "car",
                "budget": {"total_budget": 25000, "estimated_cost": 22000, "remaining": 3000, "status": "Within Budget"},
                "places": [
                    {"name": "Calangute Beach", "lat": 15.543, "lon": 73.755, "category": "Beach"},
                    {"name": "Fort Aguada", "lat": 15.492, "lon": 73.773, "category": "Historic"},
                ],
                "day_schedule": {
                    "1": [{"name": "Calangute Beach", "lat": 15.543, "lon": 73.755, "travel_time_minutes": 20}],
                    "2": [{"name": "Fort Aguada", "lat": 15.492, "lon": 73.773, "travel_time_minutes": 25}],
                },
            },
            "dashboard": {
                "destination": "Goa",
                "source": "Bengaluru",
                "days": 3,
                "travel_mode": "car",
            },
        },
    }

    trip_file.write_text(json.dumps([sample_trip]), encoding="utf-8")
    fav_file.write_text('{"favorite_trip_ids": []}', encoding="utf-8")
    note_file.write_text("{}", encoding="utf-8")
    rating_file.write_text("{}", encoding="utf-8")
    template_file.write_text("[]", encoding="utf-8")
    expense_file.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(trip_store, "FILE", trip_file)
    monkeypatch.setenv("TRIP_STORAGE_BACKEND", "json")
    monkeypatch.setattr(favorite_store, "FILE", fav_file)
    monkeypatch.setattr(note_store, "FILE", note_file)
    monkeypatch.setattr(rating_store, "FILE", rating_file)
    monkeypatch.setattr(template_store, "FILE", template_file)
    monkeypatch.setattr(expense_store, "FILE", expense_file)

    return {
        "trip_file": trip_file,
        "fav_file": fav_file,
        "note_file": note_file,
        "rating_file": rating_file,
        "template_file": template_file,
        "expense_file": expense_file,
    }
