export interface Expense {
    id: string;
    title: string;
    amount: number;
    paidBy: string;
    splitBetween: string[];
    category: "hotel" | "food" | "transport" | "activity" | "other";
}

export interface Settlement {
    from: string;
    to: string;
    amount: number;
}