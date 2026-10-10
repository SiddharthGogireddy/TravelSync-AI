import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trip_ratings.json"


def _ensure_store_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        temp_file = FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)


def load_ratings():
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Failed to load ratings: {e}")
        return {}


def save_ratings(ratings):
    _ensure_store_file()
    temp_file = FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(ratings, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)
    except Exception as e:
        logger.error(f"Failed to save ratings: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def get_rating(trip_id):
    ratings = load_ratings()
    return ratings.get(str(trip_id))


def save_rating(trip_id, rating, feedback):
    ratings = load_ratings()
    key = str(trip_id)

    ratings[key] = {
        "rating": rating,
        "feedback": feedback
    }

    save_ratings(ratings)

    return ratings[key]