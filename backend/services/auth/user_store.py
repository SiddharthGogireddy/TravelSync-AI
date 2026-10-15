import hashlib
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_FILE = DATA_DIR / "users.db"

_PROCESS_LOCK = threading.RLock()
PBKDF2_ITERATIONS = 600000


def get_db_path() -> Path:
    override = os.environ.get("TRAVELSYNC_USERS_DB")
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
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_user_db(db_path: Optional[Path] = None) -> None:
    """Initializes the users SQLite database schema with indexes."""
    with _PROCESS_LOCK:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """)
            conn.commit()


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 600,000 iterations and a 16-byte random salt."""
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
    salt = secrets.token_bytes(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256:{PBKDF2_ITERATIONS}:{salt.hex()}:{hash_bytes.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verifies a plain password against a stored PBKDF2 hash using constant-time comparison."""
    if not password or not hashed or not isinstance(password, str) or not isinstance(hashed, str):
        return False
    try:
        parts = hashed.split(":")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iters = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = parts[3]
        candidate_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iters,
        )
        return secrets.compare_digest(candidate_bytes.hex(), expected_hash)
    except Exception as e:
        logger.warning(f"Error during password verification: {e}")
        return False


def create_user(
    email: str,
    password: str,
    full_name: Optional[str] = None,
    user_id: Optional[str] = None,
    role: str = "user",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Creates a new user record.
    If user_id is passed, adopts that ID (used for claiming existing guest sessions).
    """
    if not email or "@" not in email or not str(email).strip():
        raise ValueError("Valid email address is required")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    clean_email = email.strip().lower()
    clean_name = full_name.strip() if full_name and str(full_name).strip() else None
    assigned_id = user_id.strip() if user_id and str(user_id).strip() else f"user_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    pwd_hash = hash_password(password)

    init_user_db(db_path)
    with _PROCESS_LOCK:
        with get_db_connection(db_path) as conn:
            # Check existing email
            cur = conn.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
            if cur.fetchone():
                raise ValueError("An account with this email already exists")

            # Check existing user_id if custom ID requested
            cur = conn.execute("SELECT id FROM users WHERE id = ?", (assigned_id,))
            if cur.fetchone():
                raise ValueError("An account with this user ID already exists")

            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role, created_at, updated_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (assigned_id, clean_email, pwd_hash, clean_name, role, now_iso, now_iso),
            )
            conn.commit()

    return {
        "id": assigned_id,
        "email": clean_email,
        "full_name": clean_name,
        "role": role,
        "created_at": now_iso,
        "status": "active",
    }


def authenticate_user(
    email: str,
    password: str,
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Authenticates a user with email and password.
    Returns safe user dict on success, None on invalid credentials.
    """
    if not email or not password:
        return None

    clean_email = email.strip().lower()
    init_user_db(db_path)
    with _PROCESS_LOCK:
        with get_db_connection(db_path) as conn:
            cur = conn.execute(
                "SELECT id, email, password_hash, full_name, role, created_at, status FROM users WHERE email = ?",
                (clean_email,),
            )
            row = cur.fetchone()
            if not row:
                return None

            if row["status"] != "active":
                logger.warning(f"Inactive user {clean_email} attempted login")
                return None

            if not verify_password(password, row["password_hash"]):
                return None

            return {
                "id": row["id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "role": row["role"],
                "created_at": row["created_at"],
                "status": row["status"],
            }


def get_user_by_id(user_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetches user details by user ID without password hash."""
    if not user_id:
        return None
    init_user_db(db_path)
    with _PROCESS_LOCK:
        with get_db_connection(db_path) as conn:
            cur = conn.execute(
                "SELECT id, email, full_name, role, created_at, status FROM users WHERE id = ?",
                (user_id.strip(),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)


def get_user_by_email(email: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetches user details by email without password hash."""
    if not email:
        return None
    init_user_db(db_path)
    with _PROCESS_LOCK:
        with get_db_connection(db_path) as conn:
            cur = conn.execute(
                "SELECT id, email, full_name, role, created_at, status FROM users WHERE email = ?",
                (email.strip().lower(),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)
