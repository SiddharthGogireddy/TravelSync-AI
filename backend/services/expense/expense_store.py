import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FILE = DATA_DIR / "expenses.json"


def _ensure_store_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        temp_file = FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)


def load_expenses():
    _ensure_store_file()
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Failed to load expenses: {e}")
        return {}


def save_expenses(data):
    _ensure_store_file()
    temp_file = FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, FILE)
    except Exception as e:
        logger.error(f"Failed to save expenses: {e}")
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def add_expense(trip_id, expense):
    key = str(trip_id)
    data = load_expenses()

    if key not in data:
        data[key] = []

    data[key].append(expense)

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