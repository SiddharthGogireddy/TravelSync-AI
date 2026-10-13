from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query

from backend.models.expense import ExpenseRequest
from backend.services.auth.authorization import extract_user_id, verify_trip_access

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
def create_expense(
    request: ExpenseRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    if not request.trip_id or not str(request.trip_id).strip():
        raise HTTPException(status_code=400, detail="trip_id is required")

    uid = extract_user_id(None, x_user_id, user_id)
    verify_trip_access(request.trip_id, uid, required_role="editor")

    add_expense(
        request.trip_id,
        request.expense.dict(),
    )

    return {
        "message": "Expense Added"
    }

@router.get("/{trip_id}")
def expense_summary(
    trip_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
):
    uid = extract_user_id(None, x_user_id, user_id)
    trip_record, _ = verify_trip_access(trip_id, uid, required_role="viewer")
    trip = trip_record.get("data")
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