export interface Expense {
    traveler: string;
    amount: number;
    category: string;
    note?: string;
}

export interface Settlement {
    from: string;
    to: string;
    amount: number;
}