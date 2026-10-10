import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "trip_notes.json"


def _ensure_store_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        temp_file = FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)


def load_notes():
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Failed to load notes: {e}")
        return {}


def save_notes(notes):
    _ensure_store_file()
    temp_file = FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)
    except Exception as e:
        logger.error(f"Failed to save notes: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


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