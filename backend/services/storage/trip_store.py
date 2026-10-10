import json
import logging
import os
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

# Resolve deterministic absolute path to backend/data/trips.json regardless of working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trips.json"


def _ensure_store_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        temp_file = FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)


def _read_trips() -> list:
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
            logger.warning(f"Unexpected data shape in {FILE}, expected list, got {type(data)}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in {FILE}: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to read trips from {FILE}: {e}")
        return []


def _write_trips(trips: list) -> bool:
    _ensure_store_file()
    temp_file = FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(trips, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)
        return True
    except Exception as e:
        logger.error(f"Failed to write trips to {FILE}: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        return False


def save_trip(trip_data):
    trips = _read_trips()
    trip_id = str(uuid.uuid4())

    trips.append({
        "id": trip_id,
        "data": trip_data
    })

    _write_trips(trips)
    return trip_id


def load_trip(trip_id):
    if not trip_id:
        return None
    trips = _read_trips()
    target_id = str(trip_id).strip()
    for trip in trips:
        if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
            return trip.get("data")
    return None


def update_saved_trip(
    trip_id,
    trip_data,
):
    if not trip_id:
        return False
    trips = _read_trips()
    target_id = str(trip_id).strip()
    updated = False
    for trip in trips:
        if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
            trip["data"] = trip_data
            updated = True
            break

    if updated:
        return _write_trips(trips)
    return False


def load_all_trips():
    return _read_trips()