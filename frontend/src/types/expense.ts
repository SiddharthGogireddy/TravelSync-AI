export interface Expense {
    title: string;
    amount: number;
    paid_by: string;
}

export interface Settlement {
    from: string;
    to: string;
    amount: number;
}

export interface ExpenseResponse {
    expenses: Expense[];
    balances: Record<string, number>;
    settlements: Settlement[];
}