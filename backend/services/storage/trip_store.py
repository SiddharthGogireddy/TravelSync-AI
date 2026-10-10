import json
import logging
import os
from pathlib import Path
import uuid
from datetime import datetime, timezone

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
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine creation timestamp: preserve explicit creation timestamp if passed, else assign now
    created_at = None
    if isinstance(trip_data, dict):
        created_at = trip_data.get("created_at") or (
            trip_data.get("trip", {}).get("created_at")
            if isinstance(trip_data.get("trip"), dict)
            else None
        )
    if not created_at:
        created_at = now_iso

    if isinstance(trip_data, dict):
        if "created_at" not in trip_data:
            trip_data["created_at"] = created_at
        if "trip" in trip_data and isinstance(trip_data["trip"], dict) and "created_at" not in trip_data["trip"]:
            trip_data["trip"]["created_at"] = created_at

    trips.append({
        "id": trip_id,
        "data": trip_data,
        "created_at": created_at,
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
            # Preserve original creation timestamp so updating a trip does not change creation chronology
            existing_created_at = trip.get("created_at")
            if not existing_created_at and isinstance(trip.get("data"), dict):
                existing_created_at = trip["data"].get("created_at")
            if not existing_created_at and isinstance(trip.get("data"), dict) and isinstance(trip["data"].get("trip"), dict):
                existing_created_at = trip["data"]["trip"].get("created_at")

            if existing_created_at:
                trip["created_at"] = existing_created_at
                if isinstance(trip_data, dict):
                    trip_data["created_at"] = existing_created_at
                    if "trip" in trip_data and isinstance(trip_data["trip"], dict):
                        trip_data["trip"]["created_at"] = existing_created_at

            trip["data"] = trip_data
            updated = True
            break

    if updated:
        return _write_trips(trips)
    return False


def load_all_trips():
    return _read_trips()