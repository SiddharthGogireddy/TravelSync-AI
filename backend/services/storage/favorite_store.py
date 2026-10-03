import json
import os

FILE = "backend/data/favorites.json"


def load_favorites():
    if not os.path.exists(FILE):
        return []

    with open(FILE, "r") as f:
        data = json.load(f)

    return data.get("favorite_trip_ids", [])


def save_favorites(favorite_trip_ids):
    with open(FILE, "w") as f:
        json.dump(
            {
                "favorite_trip_ids": favorite_trip_ids
            },
            f,
            indent=4
        )


def add_favorite(trip_id):
    favorites = load_favorites()

    if trip_id not in favorites:
        favorites.append(trip_id)

    save_favorites(favorites)


def remove_favorite(trip_id):
    favorites = load_favorites()

    if trip_id in favorites:
        favorites.remove(trip_id)

    save_favorites(favorites)


def is_favorite(trip_id):
    return trip_id in load_favorites()