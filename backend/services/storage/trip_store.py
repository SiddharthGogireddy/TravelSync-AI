import copy
import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Concurrency lock to guard file reads, mutations, and atomic writes
_STORE_LOCK = threading.RLock()

# Resolve deterministic absolute path to backend/data/trips.json and trips.db
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trips.json"
DEFAULT_DB_FILE = DATA_DIR / "trips.db"


class StorageCorruptedError(RuntimeError):
    """Raised when trip storage file exists but is corrupted, truncated, or unreadable."""
    pass


def get_db_path() -> Path:
    override = os.getenv("TRAVELSYNC_TRIPS_DB")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return DEFAULT_DB_FILE


def get_storage_backend() -> str:
    """Returns active storage backend ('sqlite' or 'json'). Defaults to 'sqlite' if DB exists."""
    backend = os.getenv("TRIP_STORAGE_BACKEND")
    if backend:
        return backend.strip().lower()
    if get_db_path().exists():
        return "sqlite"
    return "json"


def get_sqlite_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or get_db_path()
    conn = sqlite3.connect(
        str(target),
        timeout=30.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_sqlite_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            owner_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            data_json TEXT NOT NULL,
            members_json TEXT NOT NULL,
            invitations_json TEXT NOT NULL
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trips_owner ON trips(owner_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trips_created_at ON trips(created_at);")
    conn.commit()


# ==============================================================================
# JSON File Store Implementation (Fallback / Legacy Mode)
# ==============================================================================

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


# ==============================================================================
# Unified Repository Interface (SQLite with JSON fallback)
# ==============================================================================

def save_trip(trip_data, owner_id=None):
    backend = get_storage_backend()
    if backend == "sqlite":
        return _sqlite_save_trip(trip_data, owner_id)
    return _json_save_trip(trip_data, owner_id)


def load_trip(trip_id):
    if not trip_id:
        return None
    backend = get_storage_backend()
    if backend == "sqlite":
        return _sqlite_load_trip(trip_id)
    return _json_load_trip(trip_id)


def load_trip_record(trip_id):
    if not trip_id:
        return None
    backend = get_storage_backend()
    if backend == "sqlite":
        return _sqlite_load_trip_record(trip_id)
    return _json_load_trip_record(trip_id)


def update_saved_trip(trip_id, trip_data):
    if not trip_id:
        return False
    backend = get_storage_backend()
    if backend == "sqlite":
        return _sqlite_update_saved_trip(trip_id, trip_data)
    return _json_update_saved_trip(trip_id, trip_data)


def update_trip_sharing(trip_id: str, owner_id=None, members=None, invitations=None) -> bool:
    if not trip_id:
        return False
    backend = get_storage_backend()
    if backend == "sqlite":
        return _sqlite_update_trip_sharing(trip_id, owner_id, members, invitations)
    return _json_update_trip_sharing(trip_id, owner_id, members, invitations)


def load_all_trips(user_id=None):
    backend = get_storage_backend()
    if backend == "sqlite":
        return _sqlite_load_all_trips(user_id)
    return _json_load_all_trips(user_id)


# ==============================================================================
# SQLite Implementations
# ==============================================================================

def _sqlite_save_trip(trip_data, owner_id=None) -> str:
    with _STORE_LOCK:
        trip_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

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

        with get_sqlite_conn() as conn:
            init_sqlite_schema(conn)
            conn.execute(
                """
                INSERT INTO trips (id, owner_id, created_at, updated_at, data_json, members_json, invitations_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trip_id,
                    resolved_owner,
                    created_at,
                    now_iso,
                    json.dumps(trip_data, ensure_ascii=False),
                    json.dumps(members, ensure_ascii=False),
                    json.dumps([], ensure_ascii=False),
                ),
            )
            conn.commit()

        return trip_id


def _sqlite_load_trip(trip_id: str) -> Optional[dict]:
    target_id = str(trip_id).strip()
    with get_sqlite_conn() as conn:
        init_sqlite_schema(conn)
        cur = conn.execute("SELECT data_json FROM trips WHERE id = ?", (target_id,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row["data_json"])


def _sqlite_load_trip_record(trip_id: str) -> Optional[dict]:
    target_id = str(trip_id).strip()
    with get_sqlite_conn() as conn:
        init_sqlite_schema(conn)
        cur = conn.execute(
            "SELECT id, owner_id, created_at, data_json, members_json, invitations_json FROM trips WHERE id = ?",
            (target_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "owner_id": row["owner_id"],
            "created_at": row["created_at"],
            "data": json.loads(row["data_json"]),
            "members": json.loads(row["members_json"]),
            "invitations": json.loads(row["invitations_json"]),
        }


def _sqlite_update_saved_trip(trip_id: str, trip_data: dict) -> bool:
    with _STORE_LOCK:
        target_id = str(trip_id).strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_sqlite_conn() as conn:
            init_sqlite_schema(conn)
            cur = conn.execute("SELECT created_at, data_json FROM trips WHERE id = ?", (target_id,))
            row = cur.fetchone()
            if not row:
                return False

            existing_created_at = row["created_at"]
            if isinstance(trip_data, dict):
                trip_data["created_at"] = existing_created_at
                if "trip" in trip_data and isinstance(trip_data["trip"], dict):
                    trip_data["trip"]["created_at"] = existing_created_at

            conn.execute(
                "UPDATE trips SET data_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(trip_data, ensure_ascii=False), now_iso, target_id),
            )
            conn.commit()
            return True


def _sqlite_update_trip_sharing(trip_id: str, owner_id=None, members=None, invitations=None) -> bool:
    with _STORE_LOCK:
        target_id = str(trip_id).strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_sqlite_conn() as conn:
            init_sqlite_schema(conn)
            cur = conn.execute("SELECT owner_id, members_json, invitations_json FROM trips WHERE id = ?", (target_id,))
            row = cur.fetchone()
            if not row:
                return False

            new_owner = owner_id if owner_id is not None else row["owner_id"]
            new_members = json.dumps(members, ensure_ascii=False) if members is not None else row["members_json"]
            new_invitations = json.dumps(invitations, ensure_ascii=False) if invitations is not None else row["invitations_json"]

            conn.execute(
                "UPDATE trips SET owner_id = ?, members_json = ?, invitations_json = ?, updated_at = ? WHERE id = ?",
                (new_owner, new_members, new_invitations, now_iso, target_id),
            )
            conn.commit()
            return True


def _sqlite_load_all_trips(user_id=None) -> list:
    with get_sqlite_conn() as conn:
        init_sqlite_schema(conn)
        cur = conn.execute(
            "SELECT id, owner_id, created_at, data_json, members_json, invitations_json FROM trips ORDER BY created_at DESC"
        )
        rows = cur.fetchall()

    if not user_id:
        return [
            {
                "id": r["id"],
                "owner_id": r["owner_id"],
                "created_at": r["created_at"],
                "data": json.loads(r["data_json"]),
                "members": json.loads(r["members_json"]),
                "invitations": json.loads(r["invitations_json"]),
            }
            for r in rows
        ]

    uid = str(user_id).strip()
    visible = []
    for r in rows:
        owner = r["owner_id"]
        members = json.loads(r["members_json"]) if r["members_json"] else {}
        if not owner or owner == uid or uid in members:
            visible.append({
                "id": r["id"],
                "owner_id": r["owner_id"],
                "created_at": r["created_at"],
                "data": json.loads(r["data_json"]),
                "members": members,
                "invitations": json.loads(r["invitations_json"]),
            })
    return visible


# ==============================================================================
# JSON Fallback Implementations
# ==============================================================================

def _json_save_trip(trip_data, owner_id=None):
    with _STORE_LOCK:
        trips = _read_trips()
        trip_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

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


def _json_load_trip(trip_id):
    with _STORE_LOCK:
        trips = _read_trips()
        target_id = str(trip_id).strip()
        for trip in trips:
            if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
                return trip.get("data")
        return None


def _json_load_trip_record(trip_id):
    with _STORE_LOCK:
        trips = _read_trips()
        target_id = str(trip_id).strip()
        for trip in trips:
            if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
                return copy.deepcopy(trip)
        return None


def _json_update_saved_trip(trip_id, trip_data):
    with _STORE_LOCK:
        trips = _read_trips()
        target_id = str(trip_id).strip()
        updated = False
        for trip in trips:
            if isinstance(trip, dict) and str(trip.get("id") or "").strip() == target_id:
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


def _json_update_trip_sharing(trip_id: str, owner_id=None, members=None, invitations=None) -> bool:
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


def _json_load_all_trips(user_id=None):
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
            if not owner or owner == uid or uid in members:
                visible.append(t)
        return visible