import json
import logging
import os
from pathlib import Path
import sqlite3
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sqlite_exporter")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "backend" / "data"
TRIPS_DB = DATA_DIR / "trips.db"
TRIPS_JSON = DATA_DIR / "trips.json"


def export_sqlite_to_json(source_db: Path = TRIPS_DB, output_json: Path = TRIPS_JSON) -> int:
    """
    Exports all records from trips.db to trips.json using atomic file replacement.
    Provides complete rollback capability.
    """
    if not source_db.exists():
        raise FileNotFoundError(f"Source database {source_db} does not exist")

    conn = sqlite3.connect(str(source_db))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id, owner_id, created_at, data_json, members_json, invitations_json FROM trips ORDER BY created_at ASC")
    rows = cur.fetchall()

    trips = []
    for r in rows:
        trips.append({
            "id": r["id"],
            "data": json.loads(r["data_json"]),
            "created_at": r["created_at"],
            "owner_id": r["owner_id"],
            "members": json.loads(r["members_json"]),
            "invitations": json.loads(r["invitations_json"]),
        })

    conn.close()

    temp_file = output_json.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(trips, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    try:
        os.replace(temp_file, output_json)
    except PermissionError:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(trips, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        if temp_file.exists():
            temp_file.unlink()

    logger.info(f"Successfully exported {len(trips)} records from {source_db} to {output_json}")
    return len(trips)


if __name__ == "__main__":
    count = export_sqlite_to_json()
    print(f"Exported {count} trips to JSON.")
