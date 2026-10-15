import copy
import logging
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_FILE = DATA_DIR / "chat.db"

_PROCESS_LOCK = threading.RLock()


def get_db_path() -> Path:
    override = os.environ.get("TRAVELSYNC_CHAT_DB")
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
    # Configure SQLite for robust multi-process concurrent access
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception as e:
        logger.warning(f"Could not set WAL/busy_timeout on SQLite: {e}")
    return conn


def init_db(db_path: Optional[Path] = None):
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id TEXT PRIMARY KEY,
                        trip_id TEXT NOT NULL,
                        sender_id TEXT NOT NULL,
                        sender_name TEXT,
                        content TEXT NOT NULL,
                        target_type TEXT NOT NULL DEFAULT 'trip',
                        target_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT,
                        is_edited INTEGER NOT NULL DEFAULT 0,
                        is_deleted INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_trip_created ON chat_messages(trip_id, created_at);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_target ON chat_messages(trip_id, target_type, target_id);"
                )
        finally:
            conn.close()


# Initialize schema on module import
init_db()


def add_message(
    trip_id: str,
    sender_id: str,
    content: str,
    sender_name: Optional[str] = None,
    target_type: str = "trip",
    target_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Saves a new chat message or attraction comment atomically.
    Multi-process and multi-worker safe via SQLite transaction and WAL journal.
    """
    clean_trip_id = str(trip_id).strip()
    clean_sender_id = str(sender_id).strip()
    clean_content = str(content).strip()

    if not clean_trip_id:
        raise ValueError("trip_id cannot be blank")
    if not clean_sender_id:
        raise ValueError("sender_id cannot be blank")
    if not clean_content:
        raise ValueError("Message content cannot be empty")

    now_iso = datetime.now(timezone.utc).isoformat()
    message_id = str(uuid.uuid4())
    norm_target_type = (target_type or "trip").strip().lower()
    norm_target_id = str(target_id).strip() if target_id else None

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO chat_messages (
                        id, trip_id, sender_id, sender_name, content,
                        target_type, target_id, created_at, updated_at,
                        is_edited, is_deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, 0);
                    """,
                    (
                        message_id,
                        clean_trip_id,
                        clean_sender_id,
                        sender_name.strip() if sender_name else None,
                        clean_content,
                        norm_target_type,
                        norm_target_id,
                        now_iso,
                    ),
                )
        finally:
            conn.close()

    return {
        "id": message_id,
        "message_id": message_id,
        "trip_id": clean_trip_id,
        "sender_id": clean_sender_id,
        "sender_name": sender_name.strip() if sender_name else None,
        "content": clean_content,
        "target_type": norm_target_type,
        "target_id": norm_target_id,
        "created_at": now_iso,
        "updated_at": None,
        "is_edited": False,
        "is_deleted": False,
    }


def list_messages(
    trip_id: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
    db_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves chronological messages for a trip, optionally filtered by target_type & target_id.
    Returns (messages_list, total_count).
    """
    clean_trip_id = str(trip_id).strip()
    if not clean_trip_id:
        return [], 0

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    where_clauses = ["trip_id = ?"]
    params: List[Any] = [clean_trip_id]

    if not include_deleted:
        where_clauses.append("is_deleted = 0")

    if target_type is not None:
        norm_type = target_type.strip().lower()
        where_clauses.append("target_type = ?")
        params.append(norm_type)

    if target_id is not None:
        norm_tid = str(target_id).strip()
        where_clauses.append("target_id = ?")
        params.append(norm_tid)

    where_sql = " AND ".join(where_clauses)

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            # Count total matching
            count_cur = conn.execute(f"SELECT COUNT(*) FROM chat_messages WHERE {where_sql};", params)
            total = count_cur.fetchone()[0]

            # Fetch paginated messages ordered chronologically
            query_sql = f"""
                SELECT id, trip_id, sender_id, sender_name, content,
                       target_type, target_id, created_at, updated_at,
                       is_edited, is_deleted
                FROM chat_messages
                WHERE {where_sql}
                ORDER BY created_at ASC
                LIMIT ? OFFSET ?;
            """
            rows = conn.execute(query_sql, params + [limit, offset]).fetchall()
        finally:
            conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "message_id": r["id"],
            "trip_id": r["trip_id"],
            "sender_id": r["sender_id"],
            "sender_name": r["sender_name"],
            "content": r["content"],
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "is_edited": bool(r["is_edited"]),
            "is_deleted": bool(r["is_deleted"]),
        })

    return result, total


def get_message(message_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    clean_id = str(message_id).strip()
    if not clean_id:
        return None

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                """
                SELECT id, trip_id, sender_id, sender_name, content,
                       target_type, target_id, created_at, updated_at,
                       is_edited, is_deleted
                FROM chat_messages
                WHERE id = ?;
                """,
                (clean_id,),
            ).fetchone()
        finally:
            conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "message_id": row["id"],
        "trip_id": row["trip_id"],
        "sender_id": row["sender_id"],
        "sender_name": row["sender_name"],
        "content": row["content"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "is_edited": bool(row["is_edited"]),
        "is_deleted": bool(row["is_deleted"]),
    }


def update_message(
    message_id: str,
    new_content: str,
    sender_id: str,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Updates a message's content. Safe editing rule: Only the original sender may edit.
    """
    clean_id = str(message_id).strip()
    clean_sender = str(sender_id).strip()
    clean_content = str(new_content).strip()

    if not clean_content:
        raise ValueError("Message content cannot be empty")

    msg = get_message(clean_id, db_path=db_path)
    if not msg:
        raise KeyError("Message not found")
    if msg.get("is_deleted"):
        raise ValueError("Cannot edit a deleted message")
    if msg["sender_id"] != clean_sender:
        raise PermissionError("You can only edit your own messages")

    now_iso = datetime.now(timezone.utc).isoformat()

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE chat_messages
                    SET content = ?, updated_at = ?, is_edited = 1
                    WHERE id = ?;
                    """,
                    (clean_content, now_iso, clean_id),
                )
        finally:
            conn.close()

    msg["content"] = clean_content
    msg["updated_at"] = now_iso
    msg["is_edited"] = True
    return msg


def delete_message(
    message_id: str,
    user_id: str,
    user_role: str = "viewer",
    db_path: Optional[Path] = None,
) -> bool:
    """
    Deletes (or soft-deletes) a message.
    Safe deletion rules:
    - Original sender may delete their own message.
    - Trip owner may moderate (delete) any message on their trip.
    - Other members cannot delete messages they do not own.
    """
    clean_id = str(message_id).strip()
    clean_user = str(user_id).strip()

    msg = get_message(clean_id, db_path=db_path)
    if not msg:
        raise KeyError("Message not found")

    is_owner = (user_role or "").strip().lower() == "owner"
    is_sender = msg["sender_id"] == clean_user

    if not (is_sender or is_owner):
        raise PermissionError("Permission denied: You can only delete your own messages unless you are the trip owner")

    now_iso = datetime.now(timezone.utc).isoformat()

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE chat_messages
                    SET is_deleted = 1, updated_at = ?
                    WHERE id = ?;
                    """,
                    (now_iso, clean_id),
                )
        finally:
            conn.close()

    return True


def clear_trip_messages(trip_id: str, db_path: Optional[Path] = None):
    """Utility for testing cleanup."""
    clean_trip_id = str(trip_id).strip()
    if not clean_trip_id:
        return
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute("DELETE FROM chat_messages WHERE trip_id = ?;", (clean_trip_id,))
        finally:
            conn.close()
