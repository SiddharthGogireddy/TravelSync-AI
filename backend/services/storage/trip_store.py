import json
import uuid

FILE = "backend/data/trips.json"

def save_trip(trip_data):
    with open(FILE, "r") as f:
        trips = json.load(f)

    trip_id = str(uuid.uuid4())

    trips.append({
        "id": trip_id,
        "data": trip_data
    })

    with open(FILE, "w") as f:
        json.dump(trips, f, indent=2)

    return trip_id


def load_trip(trip_id):
    with open(FILE, "r") as f:
        trips = json.load(f)

    for trip in trips:
        if trip["id"] == trip_id:
            return trip["data"]

    return None
def update_saved_trip(
    trip_id,
    trip_data,
):

    with open(FILE, "r") as f:
        trips = json.load(f)

    for trip in trips:

        if trip["id"] == trip_id:

            trip["data"] = trip_data

            with open(FILE, "w") as f:

                json.dump(
                    trips,
                    f,
                    indent=2,
                )

            return True

    return False