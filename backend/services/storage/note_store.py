import json
import os

FILE = "backend/data/trip_notes.json"


def load_notes():
    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r") as f:
        return json.load(f)


def save_notes(notes):
    with open(FILE, "w") as f:
        json.dump(notes, f, indent=4)


def get_notes(trip_id):
    notes = load_notes()
    return notes.get(trip_id, [])


def add_note(trip_id, note):
    notes = load_notes()

    if trip_id not in notes:
        notes[trip_id] = []

    notes[trip_id].append(note)

    save_notes(notes)

    return notes[trip_id]


def delete_note(trip_id, note_index):
    notes = load_notes()

    if trip_id not in notes:
        return False

    if note_index < 0 or note_index >= len(notes[trip_id]):
        return False

    notes[trip_id].pop(note_index)

    save_notes(notes)

    return True