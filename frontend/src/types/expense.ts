export interface Expense {
    title: string;

    amount: number;

    paid_by: string;

    category: string;

    participants: string[];

    split_type: "equal" | "custom";

    custom_split?: Record<string, number>;
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