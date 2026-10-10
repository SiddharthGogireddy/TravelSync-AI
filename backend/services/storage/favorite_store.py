import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "favorites.json"


def _ensure_store_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        temp_file = FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"favorite_trip_ids": []}, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)


def load_favorites():
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("favorite_trip_ids", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"Failed to load favorites: {e}")
        return []


def save_favorites(favorite_trip_ids):
    _ensure_store_file()
    temp_file = FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "favorite_trip_ids": favorite_trip_ids
                },
                f,
                indent=4
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)
    except Exception as e:
        logger.error(f"Failed to save favorites: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def add_favorite(trip_id):
    favorites = load_favorites()

    if trip_id not in favorites:
        favorites.append(trip_id)

    save_favorites(favorites)


def remove_favorite(trip_id):
    favorites = load_favorites()

    if trip_id in favorites:
        favorites.remove(trip_id)

    save_favorites(favorites)


def is_favorite(trip_id):
    return trip_id in load_favorites()