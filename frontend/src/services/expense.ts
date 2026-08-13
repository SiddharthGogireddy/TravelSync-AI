import type { ExpenseResponse } from "../types/expense";

const API = "http://127.0.0.1:8000";

export async function getExpenses(
    tripId: string
): Promise<ExpenseResponse> {

    const response = await fetch(
        `${API}/expense/${tripId}`
    );

    return response.json();
}

export async function addExpense(
    tripId: string,
    expense: {
        title: string;
        amount: number;
        paid_by: string;
    }
) {

    return fetch(`${API}/expense/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            trip_id: tripId,
            expense,
        }),
    });
}