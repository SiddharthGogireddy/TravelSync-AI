import os
import shutil
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
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
    """Ensure real user data is backed up and never mutated by test sessions."""
    # Ensure backup directory exists and has files
    BACKEND_DATA_BACKUP.mkdir(parents=True, exist_ok=True)
    for fname in DATA_FILES:
        src = BACKEND_DATA / fname
        dst = BACKEND_DATA_BACKUP / fname
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)

    yield

    # Restore pristine files from backup at end of test session
    for fname in DATA_FILES:
        src = BACKEND_DATA_BACKUP / fname
        dst = BACKEND_DATA / fname
        if src.exists():
            shutil.copyfile(src, dst)


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Provide completely isolated storage paths for testing destructive or CRUD flows."""
    import backend.services.storage.trip_store as trip_store
    import backend.services.storage.favorite_store as favorite_store
    import backend.services.storage.note_store as note_store
    import backend.services.storage.rating_store as rating_store

    trip_file = tmp_path / "trips.json"
    fav_file = tmp_path / "favorites.json"
    note_file = tmp_path / "trip_notes.json"
    rating_file = tmp_path / "trip_ratings.json"

    # Initialize empty stores
    trip_file.write_text("[]", encoding="utf-8")
    fav_file.write_text('{"favorite_trip_ids": []}', encoding="utf-8")
    note_file.write_text("{}", encoding="utf-8")
    rating_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(trip_store, "FILE", trip_file)
    monkeypatch.setattr(favorite_store, "FILE", fav_file)
    monkeypatch.setattr(note_store, "FILE", note_file)
    monkeypatch.setattr(rating_store, "FILE", rating_file)

    return {
        "trip_file": trip_file,
        "fav_file": fav_file,
        "note_file": note_file,
        "rating_file": rating_file,
    }
