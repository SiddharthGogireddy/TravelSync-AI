from pydantic import BaseModel


class Expense(BaseModel):
    title: str
    amount: float
    paid_by: str
    category: str = "other"


class ExpenseRequest(BaseModel):
    trip_id: str
    expense: Expense