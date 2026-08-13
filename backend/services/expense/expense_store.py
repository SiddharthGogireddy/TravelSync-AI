import json
import os

FILE = "backend/data/expenses.json"


def load_expenses():

    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r") as f:
        return json.load(f)


def save_expenses(data):

    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_expense(trip_id, expense):

    print("Trip ID:", trip_id)
    print("Expense:", expense)

    data = load_expenses()

    print("Before:", data)

    if trip_id not in data:
        data[trip_id] = []

    data[trip_id].append(expense)

    print("After:", data)

    save_expenses(data)
def get_expenses(trip_id):

    data = load_expenses()

    return data.get(trip_id, [])