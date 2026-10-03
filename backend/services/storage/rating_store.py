import json
import os

FILE = "backend/data/trip_ratings.json"


def load_ratings():
    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r") as f:
        return json.load(f)


def save_ratings(ratings):
    with open(FILE, "w") as f:
        json.dump(ratings, f, indent=4)


def get_rating(trip_id):
    ratings = load_ratings()
    return ratings.get(trip_id)


def save_rating(trip_id, rating, feedback):
    ratings = load_ratings()

    ratings[trip_id] = {
        "rating": rating,
        "feedback": feedback
    }

    save_ratings(ratings)

    return ratings[trip_id]