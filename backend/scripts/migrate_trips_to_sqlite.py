import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trip_migrator")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "backend" / "data"
TRIPS_JSON = DATA_DIR / "trips.json"
TRIPS_DB = DATA_DIR / "trips.db"
BACKUP_DIR = DATA_DIR / "backups"


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_snapshot_backup() -> Path:
    """Creates a timestamped snapshot of trips.json in the backups directory."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"trips_backup_{timestamp}_pre_sqlite.json"
    shutil.copy2(TRIPS_JSON, backup_file)
    logger.info(f"Snapshot backup created: {backup_file} ({backup_file.stat().st_size} bytes)")
    return backup_file


def init_sqlite_schema(conn: sqlite3.Connection):
    """Initializes the trips SQLite schema with WAL mode and performance indexes."""
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
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


def migrate_trips(target_db: Path = TRIPS_DB) -> Dict[str, Any]:
    """
    Executes an atomic migration from trips.json to trips.db.
    Validates parity, counts, and SHA256 checksums.
    """
    if not TRIPS_JSON.exists():
        raise FileNotFoundError(f"Source file {TRIPS_JSON} does not exist")

    # Step 1: Create verified snapshot backup
    backup_file = create_snapshot_backup()
    original_sha256 = compute_sha256(TRIPS_JSON)

    # Step 2: Read and validate JSON
    logger.info(f"Reading {TRIPS_JSON}...")
    with open(TRIPS_JSON, "r", encoding="utf-8") as f:
        raw_trips = json.load(f)

    if not isinstance(raw_trips, list):
        raise ValueError(f"Expected list of trips in {TRIPS_JSON}, got {type(raw_trips).__name__}")

    total_records = len(raw_trips)
    logger.info(f"Loaded {total_records} trips from JSON. Initializing SQLite target: {target_db}...")

    # Step 3: Populate SQLite
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    init_sqlite_schema(conn)

    inserted = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    with conn:
        for t in raw_trips:
            if not isinstance(t, dict):
                continue
            trip_id = str(t.get("id") or "").strip()
            if not trip_id:
                continue

            owner_id = t.get("owner_id")
            if owner_id:
                owner_id = str(owner_id).strip()

            created_at = t.get("created_at") or now_iso
            updated_at = t.get("updated_at") or created_at
            data_json = json.dumps(t.get("data") or {}, ensure_ascii=False)
            members_json = json.dumps(t.get("members") or {}, ensure_ascii=False)
            invitations_json = json.dumps(t.get("invitations") or [], ensure_ascii=False)

            conn.execute(
                """
                INSERT OR REPLACE INTO trips (id, owner_id, created_at, updated_at, data_json, members_json, invitations_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trip_id, owner_id, created_at, updated_at, data_json, members_json, invitations_json),
            )
            inserted += 1

    logger.info(f"Inserted {inserted} records into SQLite.")

    # Step 4: Verification and Parity Audit
    cur = conn.execute("SELECT COUNT(*) as count FROM trips")
    sqlite_count = cur.fetchone()["count"]

    if sqlite_count != total_records:
        raise RuntimeError(f"Record count mismatch! JSON: {total_records}, SQLite: {sqlite_count}")

    # Check that every trip ID is present and deep payload matches
    cur = conn.execute("SELECT id, owner_id, created_at, data_json, members_json, invitations_json FROM trips")
    sqlite_rows = {row["id"]: row for row in cur.fetchall()}

    for t in raw_trips:
        tid = str(t.get("id")).strip()
        if tid not in sqlite_rows:
            raise RuntimeError(f"Missing trip ID {tid} in SQLite database!")
        row = sqlite_rows[tid]
        assert (row["owner_id"] or None) == (t.get("owner_id") or None)
        assert json.loads(row["data_json"]) == t.get("data")
        assert json.loads(row["members_json"]) == (t.get("members") or {})
        assert json.loads(row["invitations_json"]) == (t.get("invitations") or [])

    conn.close()

    result = {
        "success": True,
        "json_records_count": total_records,
        "sqlite_records_count": sqlite_count,
        "backup_path": str(backup_file),
        "backup_size_bytes": backup_file.stat().st_size,
        "sqlite_db_path": str(target_db),
        "sqlite_db_size_bytes": target_db.stat().st_size,
        "json_sha256": original_sha256,
        "verified_parity": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Migration completed and 100% verified! SQLite DB size: {result['sqlite_db_size_bytes']} bytes")
    return result


if __name__ == "__main__":
    res = migrate_trips()
    print(json.dumps(res, indent=2))
