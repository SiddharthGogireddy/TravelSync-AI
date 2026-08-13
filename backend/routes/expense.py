from fastapi import APIRouter

from backend.models.expense import ExpenseRequest

from backend.services.expense.expense_store import (
    add_expense,
    get_expenses,
)

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

    expenses = get_expenses(trip_id)

    balances = split_equally(
        expenses,
        trip["trip"]["travelers"],
    )

    settlements = calculate_settlements(
        balances
    )

    return {
        "expenses": expenses,
        "balances": balances,
        "settlements": settlements,
    }