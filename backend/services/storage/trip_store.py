import copy
import json
import logging
import os
from pathlib import Path
import threading
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Concurrency lock to guard file reads, mutations, and atomic writes
_STORE_LOCK = threading.RLock()

# Resolve deterministic absolute path to backend/data/trips.json regardless of working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trips.json"


class StorageCorruptedError(RuntimeError):
    """Raised when trip storage JSON file exists but is corrupted, truncated, or unreadable."""
    pass


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
    with _STORE_LOCK:
        _ensure_store_file()
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.critical(f"Failed to open trip storage file {FILE}: {e}")
            raise StorageCorruptedError(f"Cannot read trip storage file {FILE}: {e}") from e

        content_str = content.strip()
        if not content_str:
            logger.critical(f"Trip storage file {FILE} is empty (0 bytes). Corrupt or truncated file detected.")
            raise StorageCorruptedError(f"Trip storage file {FILE} is empty/truncated and cannot be safely parsed.")

        try:
            data = json.loads(content_str)
        except json.JSONDecodeError as e:
            logger.critical(f"Malformed JSON in {FILE}: {e}")
            raise StorageCorruptedError(f"Malformed JSON in trip storage {FILE}: {e}") from e

        if not isinstance(data, list):
            logger.critical(f"Unexpected data shape in {FILE}: expected list, got {type(data).__name__}")
            raise StorageCorruptedError(f"Unexpected data shape in {FILE}: expected list, got {type(data).__name__}")

        return data


def _write_trips(trips: list) -> bool:
    with _STORE_LOCK:
        _ensure_store_file()
        temp_file = FILE.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(trips, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            try:
                os.replace(temp_file, FILE)
            except PermissionError:
                # On Windows, os.replace into a file open by an editor/service raises Access is denied.
                # Fall back to overwriting FILE directly in-place:
                with open(FILE, "w", encoding="utf-8") as f:
                    json.dump(trips, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
            return True
        except Exception as e:
            logger.error(f"Failed to write trips to {FILE}: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False


def save_trip(trip_data, owner_id=None):
    with _STORE_LOCK:
        trips = _read_trips()
        trip_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        # Extract owner_id if not explicitly passed
        resolved_owner = None
        if owner_id:
            resolved_owner = str(owner_id).strip()
        elif isinstance(trip_data, dict):
            resolved_owner = trip_data.get("owner_id") or (
                trip_data.get("trip", {}).get("owner_id")
                if isinstance(trip_data.get("trip"), dict)
                else None
            )
            if resolved_owner:
                resolved_owner = str(resolved_owner).strip()

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
            if resolved_owner:
                trip_data["owner_id"] = resolved_owner
                if "trip" in trip_data and isinstance(trip_data["trip"], dict):
                    trip_data["trip"]["owner_id"] = resolved_owner

        members = {}
        if resolved_owner:
            members[resolved_owner] = {
                "role": "owner",
                "joined_at": created_at,
            }

        trips.append({
            "id": trip_id,
            "data": trip_data,
            "created_at": created_at,
            "owner_id": resolved_owner,
            "members": members,
            "invitations": [],
        })

        _write_trips(trips)
        return trip_id


def load_trip(trip_id):
    if not trip_id:
        return None
    with _STORE_LOCK:
        trips = _read_trips()
        target_id = str(trip_id).strip()
        for trip in trips:
            if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
                return trip.get("data")
        return None


def load_trip_record(trip_id):
    if not trip_id:
        return None
    with _STORE_LOCK:
        trips = _read_trips()
        target_id = str(trip_id).strip()
        for trip in trips:
            if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
                return copy.deepcopy(trip)
        return None


def update_saved_trip(
    trip_id,
    trip_data,
):
    if not trip_id:
        return False
    with _STORE_LOCK:
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


def update_trip_sharing(trip_id: str, owner_id=None, members=None, invitations=None) -> bool:
    if not trip_id:
        return False
    with _STORE_LOCK:
        trips = _read_trips()
        target_id = str(trip_id).strip()
        updated = False
        for trip in trips:
            if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
                if owner_id is not None:
                    trip["owner_id"] = owner_id
                if members is not None:
                    trip["members"] = members
                if invitations is not None:
                    trip["invitations"] = invitations
                updated = True
                break
        if updated:
            return _write_trips(trips)
        return False


def load_all_trips(user_id=None):
    with _STORE_LOCK:
        trips = _read_trips()
        if not user_id:
            return trips
        uid = str(user_id).strip()
        visible = []
        for t in trips:
            if not isinstance(t, dict):
                continue
            owner = t.get("owner_id")
            members = t.get("members") or {}
            # Allow if trip has no owner (legacy), or user is owner or member
            if not owner or owner == uid or uid in members:
                visible.append(t)
        return visible