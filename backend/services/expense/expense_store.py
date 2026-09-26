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
def get_category_totals(trip_id):
    expenses = get_expenses(trip_id)

    totals = {
        "hotel": 0,
        "food": 0,
        "transport": 0,
        "activities": 0,
        "emergency": 0,
        "other": 0,
    }

    for expense in expenses:
        category = expense.get("category", "other")

        if category not in totals:
            category = "other"

        totals[category] += expense["amount"]

    return {
        category: round(amount, 2)
        for category, amount in totals.items()
    }
def get_budget_comparison(trip_id, trip):

    actual = get_category_totals(trip_id)

    planned = trip["budget"].get(
        "categories",
        {}
    )

    comparison = {}

    for category in [
        "hotel",
        "food",
        "transport",
        "activities",
        "emergency",
    ]:
        planned_amount = planned.get(
            category,
            0,
        )

        actual_amount = actual.get(
            category,
            0,
        )

        comparison[category] = {
            "planned": planned_amount,
            "actual": actual_amount,
            "remaining": round(
                planned_amount - actual_amount,
                2,
            ),
        }

    return comparison