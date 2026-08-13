from pydantic import BaseModel


class Expense(BaseModel):
    title: str
    amount: float
    paid_by: str


class ExpenseRequest(BaseModel):
    trip_id: str
    expense: Expense