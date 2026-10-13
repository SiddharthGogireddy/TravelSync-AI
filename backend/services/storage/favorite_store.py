import json
import logging
import os
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

_STORE_LOCK = threading.RLock()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "favorites.json"


class StorageCorruptedError(RuntimeError):
    """Raised when favorite storage JSON file exists but is corrupted, truncated, or unreadable."""
    pass


def _ensure_store_file():
    with _STORE_LOCK:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        if not FILE.exists():
            temp_file = FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"favorite_trip_ids": []}, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            try:
                os.replace(temp_file, FILE)
            except PermissionError:
                with open(FILE, "w", encoding="utf-8") as f:
                    json.dump({"favorite_trip_ids": []}, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass


def load_favorites() -> list:
    with _STORE_LOCK:
        _ensure_store_file()
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.critical(f"Failed to open favorite storage file {FILE}: {e}")
            raise StorageCorruptedError(f"Cannot read favorite storage file {FILE}: {e}") from e

        content_str = content.strip()
        if not content_str:
            logger.critical(f"Favorite storage file {FILE} is empty (0 bytes). Corrupt or truncated file detected.")
            raise StorageCorruptedError(f"Favorite storage file {FILE} is empty/truncated and cannot be safely parsed.")

        try:
            data = json.loads(content_str)
        except json.JSONDecodeError as e:
            logger.critical(f"Malformed JSON in favorite storage {FILE}: {e}")
            raise StorageCorruptedError(f"Malformed JSON in favorite storage {FILE}: {e}") from e

        if not isinstance(data, dict):
            logger.critical(f"Unexpected data shape in favorite storage {FILE}: expected dict, got {type(data).__name__}")
            raise StorageCorruptedError(f"Unexpected data shape in {FILE}: expected dict, got {type(data).__name__}")

        if "favorite_trip_ids" not in data or not isinstance(data["favorite_trip_ids"], list):
            logger.critical(f"Unexpected data shape in favorite storage {FILE}: expected dict containing 'favorite_trip_ids' list")
            raise StorageCorruptedError(f"Unexpected data shape in {FILE}: expected dict containing 'favorite_trip_ids' list")

        return data["favorite_trip_ids"]


def save_favorites(favorite_trip_ids: list) -> bool:
    if not isinstance(favorite_trip_ids, list):
        raise ValueError(f"favorite_trip_ids must be a list, got {type(favorite_trip_ids).__name__}")
    with _STORE_LOCK:
        _ensure_store_file()
        temp_file = FILE.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "favorite_trip_ids": favorite_trip_ids
                    },
                    f,
                    indent=4
                )
                f.flush()
                os.fsync(f.fileno())
            try:
                os.replace(temp_file, FILE)
            except PermissionError:
                with open(FILE, "w", encoding="utf-8") as f:
                    json.dump({"favorite_trip_ids": favorite_trip_ids}, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
            return True
        except Exception as e:
            logger.error(f"Failed to save favorites to {FILE}: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False


def add_favorite(trip_id):
    with _STORE_LOCK:
        favorites = load_favorites()

        if trip_id not in favorites:
            favorites.append(trip_id)

        save_favorites(favorites)


def remove_favorite(trip_id):
    with _STORE_LOCK:
        favorites = load_favorites()

        if trip_id in favorites:
            favorites.remove(trip_id)

        save_favorites(favorites)


def is_favorite(trip_id):
    with _STORE_LOCK:
        return trip_id in load_favorites()