import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trip_notes.json"


class StorageCorruptedError(RuntimeError):
    """Raised when note storage JSON file exists but is corrupted, truncated, or unreadable."""
    pass


def _ensure_store_file():
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


def load_notes() -> dict:
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.critical(f"Failed to open note storage file {FILE}: {e}")
        raise StorageCorruptedError(f"Cannot read note storage file {FILE}: {e}") from e

    content_str = content.strip()
    if not content_str:
        logger.critical(f"Note storage file {FILE} is empty (0 bytes). Corrupt or truncated file detected.")
        raise StorageCorruptedError(f"Note storage file {FILE} is empty/truncated and cannot be safely parsed.")

    try:
        data = json.loads(content_str)
    except json.JSONDecodeError as e:
        logger.critical(f"Malformed JSON in note storage {FILE}: {e}")
        raise StorageCorruptedError(f"Malformed JSON in note storage {FILE}: {e}") from e

    if not isinstance(data, dict):
        logger.critical(f"Unexpected data shape in note storage {FILE}: expected dict, got {type(data).__name__}")
        raise StorageCorruptedError(f"Unexpected data shape in {FILE}: expected dict, got {type(data).__name__}")

    if any(not isinstance(v, list) for v in data.values()):
        logger.critical(f"Unexpected data shape in note storage {FILE}: note entries must be lists")
        raise StorageCorruptedError(f"Unexpected data shape in {FILE}: note entries must be lists")

    return data


def save_notes(notes: dict) -> bool:
    if not isinstance(notes, dict):
        raise ValueError(f"notes must be a dict, got {type(notes).__name__}")
    _ensure_store_file()
    temp_file = FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.replace(temp_file, FILE)
        except PermissionError:
            with open(FILE, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
        return True
    except Exception as e:
        logger.error(f"Failed to save notes to {FILE}: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        return False


def get_notes(trip_id):
    notes = load_notes()
    return notes.get(str(trip_id), [])


def add_note(trip_id, note):
    notes = load_notes()
    key = str(trip_id)

    if key not in notes:
        notes[key] = []

    notes[key].append(note)

    save_notes(notes)

    return notes[key]


def delete_note(trip_id, note_index):
    notes = load_notes()
    key = str(trip_id)

    if key not in notes:
        return False

    if note_index < 0 or note_index >= len(notes[key]):
        return False

    notes[key].pop(note_index)

    save_notes(notes)

    return True