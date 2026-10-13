import json
import logging
import os
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

_STORE_LOCK = threading.RLock()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trip_ratings.json"


class StorageCorruptedError(RuntimeError):
    """Raised when rating storage JSON file exists but is corrupted, truncated, or unreadable."""
    pass


def _ensure_store_file():
    with _STORE_LOCK:
        FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        temp_file = FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.replace(temp_file, FILE)
        except PermissionError:
            with open(FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass


def load_ratings() -> dict:
    with _STORE_LOCK:
        _ensure_store_file()
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.critical(f"Failed to open rating storage file {FILE}: {e}")
            raise StorageCorruptedError(f"Cannot read rating storage file {FILE}: {e}") from e

        content_str = content.strip()
        if not content_str:
            logger.critical(f"Rating storage file {FILE} is empty (0 bytes). Corrupt or truncated file detected.")
            raise StorageCorruptedError(f"Rating storage file {FILE} is empty/truncated and cannot be safely parsed.")

        try:
            data = json.loads(content_str)
        except json.JSONDecodeError as e:
            logger.critical(f"Malformed JSON in rating storage {FILE}: {e}")
            raise StorageCorruptedError(f"Malformed JSON in rating storage {FILE}: {e}") from e

        if not isinstance(data, dict):
            logger.critical(f"Unexpected data shape in rating storage {FILE}: expected dict, got {type(data).__name__}")
            raise StorageCorruptedError(f"Unexpected data shape in {FILE}: expected dict, got {type(data).__name__}")

        if any(not isinstance(v, dict) for v in data.values()):
            logger.critical(f"Unexpected data shape in rating storage {FILE}: rating entries must be dicts")
            raise StorageCorruptedError(f"Unexpected data shape in {FILE}: rating entries must be dicts")

        return data


def save_ratings(ratings: dict) -> bool:
    if not isinstance(ratings, dict):
        raise ValueError(f"ratings must be a dict, got {type(ratings).__name__}")
    with _STORE_LOCK:
        _ensure_store_file()
        temp_file = FILE.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(ratings, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            try:
                os.replace(temp_file, FILE)
            except PermissionError:
                with open(FILE, "w", encoding="utf-8") as f:
                    json.dump(ratings, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
            return True
        except Exception as e:
            logger.error(f"Failed to save ratings to {FILE}: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False


def get_rating(trip_id):
    with _STORE_LOCK:
        ratings = load_ratings()
        return ratings.get(str(trip_id))


def save_rating(trip_id, rating, feedback):
    with _STORE_LOCK:
        ratings = load_ratings()
        key = str(trip_id)

        ratings[key] = {
            "rating": rating,
            "feedback": feedback
        }

        save_ratings(ratings)

        return ratings[key]