export interface Expense {
    title: string;
    amount: number;
    paidBy: string;
    splitType: "equal" | "custom";
    participants: string[];
    customSplit?: Record<string, number>;
}
export interface Settlement {
    from: string;
    to: string;
    amount: number;
}
