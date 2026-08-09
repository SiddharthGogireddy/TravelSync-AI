import { useState } from "react";
import type { Expense } from "../types/expense";

interface Props {
    travelers: string[];
    onAdd: (expense: Expense) => void;
}

export default function ExpenseForm({ travelers, onAdd }: Props) {

    const [title, setTitle] = useState<string>("");
    const [amount, setAmount] = useState<number>(0);
    const [paidBy, setPaidBy] = useState<string>(travelers[0]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        const expense: Expense = {
            id: Date.now().toString(),
            title,
            amount,
            paidBy,
            splitBetween: travelers,
            category: "other"
        };

        onAdd(expense);

        setTitle("");
        setAmount(0);
    };

    return (
        <form onSubmit={handleSubmit} className="card">
            <h3>Add Expense</h3>

            <input
                placeholder="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
            />

            <input
                type="number"
                placeholder="Amount"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
            />

            <select
                value={paidBy}
                onChange={(e) => setPaidBy(e.target.value)}
            >
                {travelers.map((t) => (
                    <option key={t}>{t}</option>
                ))}
            </select>

            <button>Add</button>
        </form>
    );
}