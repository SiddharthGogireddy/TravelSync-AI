import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from backend.services.storage.trip_store import load_trip_record

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_FILE = DATA_DIR / "activity.db"

_PROCESS_LOCK = threading.RLock()


def get_db_path() -> Path:
    override = os.environ.get("TRAVELSYNC_ACTIVITY_DB")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_FILE


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(
        str(target_path),
        timeout=30.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception as e:
        logger.warning(f"Could not set WAL/busy_timeout on Activity SQLite: {e}")
    return conn


def init_db(db_path: Optional[Path] = None):
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS activity_events (
                        id TEXT PRIMARY KEY,
                        trip_id TEXT NOT NULL,
                        actor_id TEXT NOT NULL,
                        actor_name TEXT,
                        event_type TEXT NOT NULL,
                        title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        target_type TEXT,
                        target_id TEXT,
                        link TEXT,
                        metadata_json TEXT,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_activity_trip_created ON activity_events(trip_id, created_at);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_activity_dedup ON activity_events(trip_id, actor_id, event_type, target_id, created_at);"
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_notifications (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        trip_id TEXT NOT NULL,
                        event_id TEXT,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        link TEXT,
                        is_read INTEGER NOT NULL DEFAULT 0,
                        read_at TEXT,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_notif_unread ON user_notifications(user_id, is_read, created_at);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_notif_trip ON user_notifications(user_id, trip_id, created_at);"
                )
        finally:
            conn.close()


init_db()


def record_activity(
    trip_id: str,
    actor_id: str,
    event_type: str,
    title: str,
    summary: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    link: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    actor_name: Optional[str] = None,
    notify_members: bool = True,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Persists a trip activity event and creates in-app notifications for authorized trip members.
    Prevents duplicate submissions within an idempotency window (5 seconds).
    """
    clean_trip = str(trip_id).strip()
    clean_actor = str(actor_id).strip()
    clean_type = str(event_type).strip().lower()
    clean_title = str(title).strip()
    clean_summary = str(summary).strip()

    if not clean_trip or not clean_actor or not clean_type:
        raise ValueError("trip_id, actor_id, and event_type are required")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    meta_str = json.dumps(metadata) if metadata else None

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            # 1. Deduplication check: check if an identical event was recorded in the last 5 seconds
            # SQLite datetime comparison using datetime string
            recent_rows = conn.execute(
                """
                SELECT id, created_at FROM activity_events
                WHERE trip_id = ? AND actor_id = ? AND event_type = ?
                  AND (target_id IS ? OR target_id = ?)
                ORDER BY created_at DESC LIMIT 1;
                """,
                (clean_trip, clean_actor, clean_type, target_id, target_id),
            ).fetchall()

            if recent_rows:
                last_dt_str = recent_rows[0]["created_at"]
                try:
                    last_dt = datetime.fromisoformat(last_dt_str)
                    if (now - last_dt).total_seconds() < 5.0:
                        # Duplicate event suppressed
                        logger.info("Suppressed duplicate activity event (%s, %s, %s)", clean_trip, clean_actor, clean_type)
                        return {
                            "id": recent_rows[0]["id"],
                            "trip_id": clean_trip,
                            "actor_id": clean_actor,
                            "event_type": clean_type,
                            "title": clean_title,
                            "summary": clean_summary,
                            "duplicate": True,
                        }
                except Exception:
                    pass

            event_id = str(uuid.uuid4())
            with conn:
                conn.execute(
                    """
                    INSERT INTO activity_events (
                        id, trip_id, actor_id, actor_name, event_type,
                        title, summary, target_type, target_id, link,
                        metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        event_id,
                        clean_trip,
                        clean_actor,
                        actor_name.strip() if actor_name else None,
                        clean_type,
                        clean_title,
                        clean_summary,
                        target_type,
                        target_id,
                        link,
                        meta_str,
                        now_iso,
                    ),
                )

                # 2. Fan-out in-app notifications to trip members (excluding actor)
                if notify_members:
                    trip_rec = load_trip_record(clean_trip)
                    if trip_rec:
                        recipients = set()
                        owner = trip_rec.get("owner_id")
                        if owner and owner != clean_actor:
                            recipients.add(owner)
                        members = trip_rec.get("members") or {}
                        for m_id in members.keys():
                            if m_id and m_id != clean_actor:
                                recipients.add(m_id)

                        notif_link = link or f"/trip/{clean_trip}"
                        for recipient_uid in recipients:
                            notif_id = str(uuid.uuid4())
                            conn.execute(
                                """
                                INSERT INTO user_notifications (
                                    id, user_id, trip_id, event_id, title,
                                    message, link, is_read, read_at, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?);
                                """,
                                (
                                    notif_id,
                                    recipient_uid,
                                    clean_trip,
                                    event_id,
                                    clean_title,
                                    clean_summary,
                                    notif_link,
                                    now_iso,
                                ),
                            )
        finally:
            conn.close()

    return {
        "id": event_id,
        "trip_id": clean_trip,
        "actor_id": clean_actor,
        "actor_name": actor_name,
        "event_type": clean_type,
        "title": clean_title,
        "summary": clean_summary,
        "target_type": target_type,
        "target_id": target_id,
        "link": link,
        "metadata": metadata,
        "created_at": now_iso,
    }


def list_trip_activity(
    trip_id: str,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns paginated activity events for a trip, newest first.
    """
    clean_trip = str(trip_id).strip()
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            count_row = conn.execute(
                "SELECT COUNT(*) FROM activity_events WHERE trip_id = ?;",
                (clean_trip,),
            ).fetchone()
            total = count_row[0] if count_row else 0

            rows = conn.execute(
                """
                SELECT id, trip_id, actor_id, actor_name, event_type,
                       title, summary, target_type, target_id, link,
                       metadata_json, created_at
                FROM activity_events
                WHERE trip_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (clean_trip, limit, offset),
            ).fetchall()
        finally:
            conn.close()

    result = []
    for r in rows:
        meta = None
        if r["metadata_json"]:
            try:
                meta = json.loads(r["metadata_json"])
            except Exception:
                pass
        result.append({
            "id": r["id"],
            "trip_id": r["trip_id"],
            "actor_id": r["actor_id"],
            "actor_name": r["actor_name"],
            "event_type": r["event_type"],
            "title": r["title"],
            "summary": r["summary"],
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "link": r["link"],
            "metadata": meta,
            "created_at": r["created_at"],
        })

    return result, total


def list_user_notifications(
    user_id: str,
    is_read: Optional[bool] = None,
    trip_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Returns user notifications with total and unread count.
    Ordered newest first.
    """
    clean_user = str(user_id).strip()
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    where_clauses = ["user_id = ?"]
    params: List[Any] = [clean_user]

    if is_read is not None:
        where_clauses.append("is_read = ?")
        params.append(1 if is_read else 0)

    if trip_id is not None:
        where_clauses.append("trip_id = ?")
        params.append(str(trip_id).strip())

    where_sql = " AND ".join(where_clauses)

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            # Total matching query
            count_cur = conn.execute(
                f"SELECT COUNT(*) FROM user_notifications WHERE {where_sql};",
                params,
            )
            total = count_cur.fetchone()[0]

            # Total unread for this user (overall or for trip)
            unread_params = [clean_user]
            unread_trip_sql = ""
            if trip_id is not None:
                unread_trip_sql = " AND trip_id = ?"
                unread_params.append(str(trip_id).strip())

            unread_cur = conn.execute(
                f"SELECT COUNT(*) FROM user_notifications WHERE user_id = ? AND is_read = 0{unread_trip_sql};",
                unread_params,
            )
            unread_count = unread_cur.fetchone()[0]

            query_sql = f"""
                SELECT id, user_id, trip_id, event_id, title,
                       message, link, is_read, read_at, created_at
                FROM user_notifications
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """
            rows = conn.execute(query_sql, params + [limit, offset]).fetchall()
        finally:
            conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "notification_id": r["id"],
            "user_id": r["user_id"],
            "trip_id": r["trip_id"],
            "event_id": r["event_id"],
            "title": r["title"],
            "message": r["message"],
            "link": r["link"],
            "is_read": bool(r["is_read"]),
            "read_at": r["read_at"],
            "created_at": r["created_at"],
        })

    return result, total, unread_count


def mark_notification_read(
    notification_id: str,
    user_id: str,
    db_path: Optional[Path] = None,
) -> bool:
    """
    Marks a single notification as read.
    Safe ownership rule: The notification MUST belong to user_id.
    """
    clean_id = str(notification_id).strip()
    clean_user = str(user_id).strip()

    now_iso = datetime.now(timezone.utc).isoformat()

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                "SELECT id, user_id FROM user_notifications WHERE id = ?;",
                (clean_id,),
            ).fetchone()

            if not row:
                raise KeyError("Notification not found")
            if row["user_id"] != clean_user:
                raise PermissionError("Permission denied: You can only mark your own notifications as read")

            with conn:
                conn.execute(
                    """
                    UPDATE user_notifications
                    SET is_read = 1, read_at = ?
                    WHERE id = ? AND user_id = ?;
                    """,
                    (now_iso, clean_id, clean_user),
                )
        finally:
            conn.close()

    return True


def mark_all_notifications_read(
    user_id: str,
    trip_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """
    Marks all notifications for user_id as read (optionally scoped to a trip).
    Returns count of updated notifications.
    """
    clean_user = str(user_id).strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    where_sql = "user_id = ? AND is_read = 0"
    params: List[Any] = [clean_user]

    if trip_id is not None:
        where_sql += " AND trip_id = ?"
        params.append(str(trip_id).strip())

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                cur = conn.execute(
                    f"UPDATE user_notifications SET is_read = 1, read_at = ? WHERE {where_sql};",
                    [now_iso] + params,
                )
                affected = cur.rowcount
        finally:
            conn.close()

    return max(0, affected)


def clear_trip_activity(trip_id: str, db_path: Optional[Path] = None):
    """Utility for test cleanup."""
    clean_trip = str(trip_id).strip()
    if not clean_trip:
        return
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute("DELETE FROM activity_events WHERE trip_id = ?;", (clean_trip,))
                conn.execute("DELETE FROM user_notifications WHERE trip_id = ?;", (clean_trip,))
        finally:
            conn.close()


def clear_user_notifications(user_id: str, db_path: Optional[Path] = None):
    """Utility for test cleanup."""
    clean_user = str(user_id).strip()
    if not clean_user:
        return
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute("DELETE FROM user_notifications WHERE user_id = ?;", (clean_user,))
        finally:
            conn.close()

