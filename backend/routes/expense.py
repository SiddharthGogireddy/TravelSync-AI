from fastapi import APIRouter

from backend.models.expense import ExpenseRequest

from backend.services.expense.expense_store import (
    add_expense,
    get_budget_comparison,
    get_expenses,
    get_category_totals,
)
from backend.services.expense.budget_alerts import get_budget_alerts
from backend.services.expense.splitter import split_equally
from backend.services.expense.settlement import calculate_settlements

from backend.services.storage.trip_store import load_trip

router = APIRouter(
    prefix="/expense",
    tags=["Expense"],
)


@router.post("/")
def create_expense(request: ExpenseRequest):

    add_expense(
        request.trip_id,
        request.expense.dict(),
    )

    return {
        "message": "Expense Added"
    }

@router.get("/{trip_id}")
def expense_summary(trip_id: str):

    trip = load_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    raw_trip = trip.get("trip", trip) if isinstance(trip, dict) else {}
    travelers = raw_trip.get("travelers", []) if isinstance(raw_trip, dict) else []
    if not isinstance(travelers, list):
        travelers = []

    expenses = get_expenses(trip_id)

    balances = split_equally(
        expenses,
        travelers,
    )

    settlements = calculate_settlements(
        balances
    )

    category_totals = get_category_totals(
        trip_id
    )

    budget_comparison = get_budget_comparison(
        trip_id,
        raw_trip,
    )
    alerts = get_budget_alerts(
        budget_comparison
    )
    return {
        "expenses": expenses,
        "balances": balances,
        "settlements": settlements,
        "category_totals": category_totals,
        "budget_comparison": budget_comparison,
        "alerts": alerts,
    }