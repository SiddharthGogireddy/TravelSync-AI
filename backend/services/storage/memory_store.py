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
DEFAULT_DB_FILE = DATA_DIR / "memories.db"
DEFAULT_UPLOADS_DIR = DATA_DIR / "memories_uploads"

_PROCESS_LOCK = threading.RLock()

# Photo validation constants
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}


def get_db_path() -> Path:
    override = os.environ.get("TRAVELSYNC_MEMORY_DB")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_FILE


def get_uploads_dir() -> Path:
    override = os.environ.get("TRAVELSYNC_MEMORY_UPLOADS")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    DEFAULT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_UPLOADS_DIR


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
        logger.warning(f"Could not set WAL/busy_timeout on SQLite: {e}")
    return conn


def init_db(db_path: Optional[Path] = None):
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS journal_entries (
                        id TEXT PRIMARY KEY,
                        trip_id TEXT NOT NULL,
                        author_id TEXT NOT NULL,
                        author_name TEXT,
                        day_number INTEGER,
                        attraction_name TEXT,
                        title TEXT,
                        content TEXT NOT NULL,
                        photo_url TEXT,
                        photo_filename TEXT,
                        is_private INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT,
                        is_deleted INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_journal_trip_created ON journal_entries(trip_id, created_at DESC);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_journal_author ON journal_entries(author_id);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_journal_privacy ON journal_entries(trip_id, is_private, is_deleted);"
                )
        finally:
            conn.close()


init_db()


def validate_photo_file(file_bytes: bytes, original_filename: str, content_type: Optional[str] = None) -> str:
    """
    Validates file size, file extension, and image magic bytes.
    Raises ValueError with descriptive reason if invalid.
    Returns normalized lower-case extension (e.g. '.jpg', '.png').
    """
    if not file_bytes:
        raise ValueError("Photo upload cannot be empty")

    if len(file_bytes) > MAX_PHOTO_SIZE_BYTES:
        raise ValueError(
            f"File size exceeds maximum allowed limit of {MAX_PHOTO_SIZE_BYTES // (1024 * 1024)}MB"
        )

    clean_name = os.path.basename(original_filename or "").strip()
    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValueError(
            f"Invalid file extension '{ext}'. Allowed image extensions: {', '.join(sorted(ALLOWED_PHOTO_EXTENSIONS))}"
        )

    if content_type:
        clean_mime = content_type.strip().lower().split(";")[0]
        if clean_mime not in ALLOWED_MIME_TYPES and clean_mime != "application/octet-stream":
            raise ValueError(f"Unsupported MIME type '{clean_mime}'. Must be an image.")

    # Magic byte inspection
    is_valid_magic = False
    if ext in (".jpg", ".jpeg"):
        if file_bytes.startswith(b"\xff\xd8\xff"):
            is_valid_magic = True
    elif ext == ".png":
        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            is_valid_magic = True
    elif ext == ".gif":
        if file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"):
            is_valid_magic = True
    elif ext == ".webp":
        if len(file_bytes) >= 12 and file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
            is_valid_magic = True

    if not is_valid_magic:
        raise ValueError(
            f"File content does not match expected image format for extension '{ext}' (magic bytes mismatch)"
        )

    return ext


def save_memory_photo(
    file_bytes: bytes,
    original_filename: str,
    content_type: Optional[str] = None,
    trip_id: Optional[str] = None,
) -> Tuple[str, str, int]:
    """
    Validates file bytes, creates a collision-resistant safe filename,
    writes the file to the uploads directory with path traversal protection,
    and returns (safe_filename, photo_url, size_bytes).
    """
    ext = validate_photo_file(file_bytes, original_filename, content_type)
    uploads_dir = get_uploads_dir()

    # Generate cryptographically strong random filename
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = (uploads_dir / safe_filename).resolve()

    # Verify no path traversal
    if not str(target_path).startswith(str(uploads_dir.resolve())):
        raise ValueError("Invalid target filepath: path traversal detected")

    # Atomic write to disk
    temp_path = target_path.with_suffix(".tmp")
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, target_path)

    # Relative photo URL served via trip-scoped route
    clean_trip = str(trip_id).strip() if trip_id else "global"
    photo_url = f"/trip/{clean_trip}/journal/photos/{safe_filename}"
    return safe_filename, photo_url, len(file_bytes)


def get_memory_photo_path(filename: str) -> Optional[Path]:
    """
    Safely locates a photo file on disk, preventing directory traversal.
    Returns absolute Path if found and safe, None otherwise.
    """
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return None

    uploads_dir = get_uploads_dir().resolve()
    target_path = (uploads_dir / filename).resolve()

    try:
        # Check that target_path is within uploads_dir
        if not str(target_path).startswith(str(uploads_dir)):
            return None
        if target_path.is_file():
            return target_path
    except Exception:
        return None

    return None


def create_entry(
    trip_id: str,
    author_id: str,
    content: str,
    author_name: Optional[str] = None,
    day_number: Optional[int] = None,
    attraction_name: Optional[str] = None,
    title: Optional[str] = None,
    photo_url: Optional[str] = None,
    photo_filename: Optional[str] = None,
    is_private: bool = False,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    clean_trip = str(trip_id).strip()
    clean_author = str(author_id).strip()
    clean_content = str(content).strip()

    if not clean_trip or not clean_author:
        raise ValueError("trip_id and author_id are required")
    if not clean_content:
        raise ValueError("content cannot be empty")
    if len(clean_content) > 10000:
        raise ValueError("content exceeds maximum limit of 10,000 characters")

    entry_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    private_int = 1 if is_private else 0

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO journal_entries (
                        id, trip_id, author_id, author_name,
                        day_number, attraction_name, title, content,
                        photo_url, photo_filename, is_private,
                        created_at, updated_at, is_deleted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0);
                    """,
                    (
                        entry_id,
                        clean_trip,
                        clean_author,
                        str(author_name).strip() if author_name else None,
                        int(day_number) if day_number is not None else None,
                        str(attraction_name).strip() if attraction_name else None,
                        str(title).strip() if title else None,
                        clean_content,
                        str(photo_url).strip() if photo_url else None,
                        str(photo_filename).strip() if photo_filename else None,
                        private_int,
                        now_iso,
                    ),
                )
        finally:
            conn.close()

    return {
        "id": entry_id,
        "trip_id": clean_trip,
        "author_id": clean_author,
        "author_name": author_name,
        "day_number": day_number,
        "attraction_name": attraction_name,
        "title": title,
        "content": clean_content,
        "photo_url": photo_url,
        "photo_filename": photo_filename,
        "is_private": bool(is_private),
        "created_at": now_iso,
        "updated_at": None,
    }


def list_entries(
    trip_id: str,
    requester_id: str,
    day_number: Optional[int] = None,
    attraction_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    clean_trip = str(trip_id).strip()
    clean_requester = str(requester_id).strip()

    if not clean_trip or not clean_requester:
        return [], 0

    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    where_clauses = [
        "trip_id = ?",
        "is_deleted = 0",
        "(is_private = 0 OR author_id = ?)",
    ]
    params: List[Any] = [clean_trip, clean_requester]

    if day_number is not None:
        where_clauses.append("day_number = ?")
        params.append(int(day_number))

    if attraction_name:
        where_clauses.append("attraction_name = ?")
        params.append(str(attraction_name).strip())

    where_sql = " AND ".join(where_clauses)

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            count_cursor = conn.execute(
                f"SELECT COUNT(*) FROM journal_entries WHERE {where_sql};",
                params,
            )
            total = count_cursor.fetchone()[0]

            query_sql = f"""
                SELECT id, trip_id, author_id, author_name,
                       day_number, attraction_name, title, content,
                       photo_url, photo_filename, is_private,
                       created_at, updated_at
                FROM journal_entries
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """
            rows = conn.execute(query_sql, params + [limit, offset]).fetchall()

            entries = []
            for row in rows:
                entries.append(
                    {
                        "id": row["id"],
                        "trip_id": row["trip_id"],
                        "author_id": row["author_id"],
                        "author_name": row["author_name"],
                        "day_number": row["day_number"],
                        "attraction_name": row["attraction_name"],
                        "title": row["title"],
                        "content": row["content"],
                        "photo_url": row["photo_url"],
                        "photo_filename": row["photo_filename"],
                        "is_private": bool(row["is_private"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            return entries, total
        finally:
            conn.close()


def get_entry(entry_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    clean_id = str(entry_id).strip()
    if not clean_id:
        return None

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            row = conn.execute(
                """
                SELECT id, trip_id, author_id, author_name,
                       day_number, attraction_name, title, content,
                       photo_url, photo_filename, is_private,
                       created_at, updated_at, is_deleted
                FROM journal_entries
                WHERE id = ? AND is_deleted = 0;
                """,
                (clean_id,),
            ).fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "trip_id": row["trip_id"],
                "author_id": row["author_id"],
                "author_name": row["author_name"],
                "day_number": row["day_number"],
                "attraction_name": row["attraction_name"],
                "title": row["title"],
                "content": row["content"],
                "photo_url": row["photo_url"],
                "photo_filename": row["photo_filename"],
                "is_private": bool(row["is_private"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        finally:
            conn.close()


def update_entry(
    entry_id: str,
    author_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    day_number: Optional[int] = None,
    attraction_name: Optional[str] = None,
    photo_url: Optional[str] = None,
    photo_filename: Optional[str] = None,
    is_private: Optional[bool] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    clean_id = str(entry_id).strip()
    clean_author = str(author_id).strip()

    if not clean_id or not clean_author:
        raise ValueError("entry_id and author_id are required")

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            existing = conn.execute(
                "SELECT author_id, is_deleted FROM journal_entries WHERE id = ?;",
                (clean_id,),
            ).fetchone()

            if not existing or existing["is_deleted"] == 1:
                raise KeyError(f"Journal entry {clean_id} not found")

            if existing["author_id"] != clean_author:
                raise PermissionError("Only the original author can edit this journal entry")

            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(str(title).strip() if title else None)

            if content is not None:
                clean_c = str(content).strip()
                if not clean_c:
                    raise ValueError("content cannot be empty")
                if len(clean_c) > 10000:
                    raise ValueError("content exceeds maximum limit of 10,000 characters")
                updates.append("content = ?")
                params.append(clean_c)

            if day_number is not None:
                updates.append("day_number = ?")
                params.append(int(day_number))

            if attraction_name is not None:
                updates.append("attraction_name = ?")
                params.append(str(attraction_name).strip() if attraction_name else None)

            if photo_url is not None:
                updates.append("photo_url = ?")
                params.append(str(photo_url).strip() if photo_url else None)

            if photo_filename is not None:
                updates.append("photo_filename = ?")
                params.append(str(photo_filename).strip() if photo_filename else None)

            if is_private is not None:
                updates.append("is_private = ?")
                params.append(1 if is_private else 0)

            now_iso = datetime.now(timezone.utc).isoformat()
            updates.append("updated_at = ?")
            params.append(now_iso)

            params.append(clean_id)

            with conn:
                conn.execute(
                    f"UPDATE journal_entries SET {', '.join(updates)} WHERE id = ?;",
                    params,
                )

            return get_entry(clean_id, db_path=db_path)
        finally:
            conn.close()


def delete_entry(
    entry_id: str,
    requester_id: str,
    is_owner: bool = False,
    db_path: Optional[Path] = None,
) -> bool:
    clean_id = str(entry_id).strip()
    clean_req = str(requester_id).strip()

    if not clean_id or not clean_req:
        raise ValueError("entry_id and requester_id are required")

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            existing = conn.execute(
                "SELECT author_id, is_deleted FROM journal_entries WHERE id = ?;",
                (clean_id,),
            ).fetchone()

            if not existing or existing["is_deleted"] == 1:
                raise KeyError(f"Journal entry {clean_id} not found")

            # Allow author or trip owner to delete
            if existing["author_id"] != clean_req and not is_owner:
                raise PermissionError("Only the author or trip owner can delete this journal entry")

            now_iso = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    "UPDATE journal_entries SET is_deleted = 1, updated_at = ? WHERE id = ?;",
                    (now_iso, clean_id),
                )
            return True
        finally:
            conn.close()


def clear_trip_memories(trip_id: str, db_path: Optional[Path] = None):
    """Utility for test suites."""
    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            with conn:
                conn.execute("DELETE FROM journal_entries WHERE trip_id = ?;", (str(trip_id).strip(),))
        finally:
            conn.close()


def list_album_entries(
    trip_id: str,
    requester_id: str,
    day_number: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves chronological album photo memories.
    Enforces privacy: private entries are only visible if requester is the author.
    Only includes entries with an attached photo.
    """
    clean_trip = str(trip_id).strip()
    clean_requester = str(requester_id).strip()

    if not clean_trip or not clean_requester:
        return [], 0

    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    where_clauses = [
        "trip_id = ?",
        "is_deleted = 0",
        "(is_private = 0 OR author_id = ?)",
        "photo_filename IS NOT NULL",
        "photo_filename != ''",
    ]
    params: List[Any] = [clean_trip, clean_requester]

    if day_number is not None:
        where_clauses.append("day_number = ?")
        params.append(int(day_number))

    where_sql = " AND ".join(where_clauses)

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            count_cursor = conn.execute(
                f"SELECT COUNT(*) FROM journal_entries WHERE {where_sql};",
                params,
            )
            total = count_cursor.fetchone()[0]

            query_sql = f"""
                SELECT id, trip_id, author_id, author_name,
                       day_number, attraction_name, title, content,
                       photo_url, photo_filename, is_private,
                       created_at
                FROM journal_entries
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """
            rows = conn.execute(query_sql, params + [limit, offset]).fetchall()

            items = []
            for row in rows:
                items.append(
                    {
                        "id": row["id"],
                        "trip_id": row["trip_id"],
                        "author_id": row["author_id"],
                        "author_name": row["author_name"],
                        "day_number": row["day_number"],
                        "attraction_name": row["attraction_name"],
                        "title": row["title"],
                        "content": row["content"],
                        "photo_url": row["photo_url"],
                        "photo_filename": row["photo_filename"],
                        "is_private": bool(row["is_private"]),
                        "created_at": row["created_at"],
                    }
                )

            return items, total
        finally:
            conn.close()


def get_journal_entries_for_export(
    trip_id: str,
    requester_id: str,
    day_number: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Fetches all authorized journal entries for PDF export ordered chronologically by day and creation time.
    Enforces privacy: private entries are strictly excluded unless authored by requester_id.
    """
    clean_trip = str(trip_id).strip()
    clean_requester = str(requester_id).strip()

    if not clean_trip or not clean_requester:
        return []

    where_clauses = [
        "trip_id = ?",
        "is_deleted = 0",
        "(is_private = 0 OR author_id = ?)",
    ]
    params: List[Any] = [clean_trip, clean_requester]

    if day_number is not None:
        where_clauses.append("day_number = ?")
        params.append(int(day_number))

    where_sql = " AND ".join(where_clauses)

    with _PROCESS_LOCK:
        conn = get_db_connection(db_path)
        try:
            query_sql = f"""
                SELECT id, trip_id, author_id, author_name,
                       day_number, attraction_name, title, content,
                       photo_url, photo_filename, is_private,
                       created_at, updated_at
                FROM journal_entries
                WHERE {where_sql}
                ORDER BY CASE WHEN day_number IS NOT NULL THEN day_number ELSE 9999 END ASC, created_at ASC;
            """
            rows = conn.execute(query_sql, params).fetchall()

            entries = []
            for row in rows:
                entries.append(
                    {
                        "id": row["id"],
                        "trip_id": row["trip_id"],
                        "author_id": row["author_id"],
                        "author_name": row["author_name"],
                        "day_number": row["day_number"],
                        "attraction_name": row["attraction_name"],
                        "title": row["title"],
                        "content": row["content"],
                        "photo_url": row["photo_url"],
                        "photo_filename": row["photo_filename"],
                        "is_private": bool(row["is_private"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            return entries
        finally:
            conn.close()

