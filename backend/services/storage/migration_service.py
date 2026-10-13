import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.services.storage.trip_store import (
    load_trip_record,
    _read_trips,
    _write_trips,
    _STORE_LOCK,
    FILE as TRIPS_FILE,
    DATA_DIR,
)

logger = logging.getLogger(__name__)

BACKUP_DIR = DATA_DIR / "backups"


def ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def create_trips_backup(label: str = "manual") -> Dict[str, Any]:
    """
    Creates a timestamped snapshot backup of trips.json before any migration or data transformation.
    Guarantees no data loss.
    """
    with _STORE_LOCK:
        ensure_backup_dir()
        if not TRIPS_FILE.exists():
            raise FileNotFoundError(f"Cannot backup non-existent trips file {TRIPS_FILE}")

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_label = "".join(c for c in label if c.isalnum() or c in ("-", "_"))
        backup_filename = f"trips_backup_{now_str}_{clean_label}.json"
        backup_path = BACKUP_DIR / backup_filename

        shutil.copy2(TRIPS_FILE, backup_path)
        file_size = backup_path.stat().st_size

        logger.info(f"Created trips backup at {backup_path} ({file_size} bytes)")

        trips = _read_trips()

        return {
            "success": True,
            "backup_file": backup_filename,
            "backup_path": str(backup_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trips_count": len(trips),
            "file_size_bytes": file_size,
        }


def get_legacy_trips_preview() -> Dict[str, Any]:
    """
    Scans storage and returns a preview of legacy trips without modifying any data.
    """
    with _STORE_LOCK:
        trips = _read_trips()
        total_count = len(trips)
        unowned_list: List[Dict[str, Any]] = []

        for t in trips:
            if not isinstance(t, dict):
                continue
            owner_id = t.get("owner_id")
            if not owner_id:
                trip_data = t.get("data") or {}
                inner_trip = trip_data.get("trip", trip_data) if isinstance(trip_data, dict) else {}
                unowned_list.append({
                    "id": t.get("id"),
                    "source": inner_trip.get("source", "N/A"),
                    "destination": inner_trip.get("destination", "N/A"),
                    "days": inner_trip.get("days", 1),
                    "created_at": t.get("created_at"),
                })

        return {
            "total_trips": total_count,
            "owned_trips_count": total_count - len(unowned_list),
            "unowned_legacy_trips_count": len(unowned_list),
            "unowned_legacy_trips": unowned_list,
            "backup_recommended": len(unowned_list) > 0,
            "preview_generated_at": datetime.now(timezone.utc).isoformat(),
        }


def claim_legacy_trip(trip_id: str, new_owner_id: str) -> Dict[str, Any]:
    """
    Explicitly claims an unowned legacy trip for an authenticated user.
    Creates an automatic backup before modifying the store.
    Rejects claiming if the trip already has an assigned owner.
    """
    if not trip_id or not str(trip_id).strip():
        raise ValueError("trip_id is required")
    if not new_owner_id or not str(new_owner_id).strip():
        raise ValueError("new_owner_id is required")

    clean_trip_id = str(trip_id).strip()
    clean_owner = str(new_owner_id).strip()

    with _STORE_LOCK:
        trips = _read_trips()
        target_trip = None
        for t in trips:
            if isinstance(t, dict) and str(t.get("id") or "").strip() == clean_trip_id:
                target_trip = t
                break

        if not target_trip:
            raise FileNotFoundError(f"Trip '{clean_trip_id}' not found")

        current_owner = target_trip.get("owner_id")
        if current_owner:
            raise PermissionError(f"Trip '{clean_trip_id}' is already owned by '{current_owner}'")

        # Automatically create backup snapshot before transformation
        create_trips_backup(label=f"claim_{clean_trip_id[:8]}")

        now_iso = datetime.now(timezone.utc).isoformat()
        target_trip["owner_id"] = clean_owner

        members = dict(target_trip.get("members") or {})
        members[clean_owner] = {
            "role": "owner",
            "joined_at": now_iso,
        }
        target_trip["members"] = members

        # Also sync owner into inner data if present
        if isinstance(target_trip.get("data"), dict):
            target_trip["data"]["owner_id"] = clean_owner
            if "trip" in target_trip["data"] and isinstance(target_trip["data"]["trip"], dict):
                target_trip["data"]["trip"]["owner_id"] = clean_owner

        _write_trips(trips)
        logger.info(f"Trip {clean_trip_id} successfully claimed by {clean_owner}")

        return {
            "success": True,
            "trip_id": clean_trip_id,
            "owner_id": clean_owner,
            "claimed_at": now_iso,
        }


def batch_claim_legacy_trips(target_owner_id: str, trip_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Batch-claims unowned legacy trips for a designated owner.
    Creates an automatic backup snapshot before execution.
    """
    if not target_owner_id or not str(target_owner_id).strip():
        raise ValueError("target_owner_id is required")

    clean_owner = str(target_owner_id).strip()

    with _STORE_LOCK:
        trips = _read_trips()
        eligible: List[dict] = []
        target_set = set(trip_ids) if trip_ids else None

        for t in trips:
            if not isinstance(t, dict):
                continue
            t_id = str(t.get("id") or "").strip()
            if not t.get("owner_id"):
                if target_set is None or t_id in target_set:
                    eligible.append(t)

        if not eligible:
            return {
                "success": True,
                "claimed_count": 0,
                "message": "No unowned legacy trips found to claim",
            }

        backup_info = create_trips_backup(label="batch_claim")
        now_iso = datetime.now(timezone.utc).isoformat()
        claimed_ids = []

        for t in eligible:
            t["owner_id"] = clean_owner
            members = dict(t.get("members") or {})
            members[clean_owner] = {
                "role": "owner",
                "joined_at": now_iso,
            }
            t["members"] = members
            if isinstance(t.get("data"), dict):
                t["data"]["owner_id"] = clean_owner
                if "trip" in t["data"] and isinstance(t["data"]["trip"], dict):
                    t["data"]["trip"]["owner_id"] = clean_owner
            claimed_ids.append(t.get("id"))

        _write_trips(trips)
        logger.info(f"Batch-claimed {len(claimed_ids)} legacy trips to {clean_owner}")

        return {
            "success": True,
            "claimed_count": len(claimed_ids),
            "claimed_trip_ids": claimed_ids,
            "target_owner_id": clean_owner,
            "backup_file": backup_info["backup_file"],
        }
