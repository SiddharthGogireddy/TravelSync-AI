import type { ExpenseResponse } from "../types/expense";
import { API } from "./api";
import { apiFetch } from "./api";

export { API };

export async function getExpenses(
    tripId: string
): Promise<ExpenseResponse> {
    return apiFetch<ExpenseResponse>(`/expense/${tripId}`);
}

export async function addExpense(
    tripId: string,
    expense: {
        title: string;
        amount: number;
        paid_by: string;
        category?: string;
    }
) {
    return apiFetch(`/expense/`, {
        method: "POST",
        body: JSON.stringify({
            trip_id: tripId,
            expense,
        }),
    });
}