import { useState } from "react";
import type { Expense } from "../types/expense";

interface Props {
    travelers: string[];
    onAdd: (expense: Expense) => void;
}

export default function ExpenseForm({ travelers, onAdd }: Props) {
    const [traveler, setTraveler] = useState(travelers[0] || "");
    const [amount, setAmount] = useState(0);
    const [category, setCategory] = useState("food");

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();

        onAdd({
            traveler,
            amount,
            category,
        });

        setAmount(0);
    }

    return (
        <form onSubmit={handleSubmit}>
            <h3>Add Expense</h3>

            <select
                value={traveler}
                onChange={(e) => setTraveler(e.target.value)}
            >
                {travelers.map((t) => (
                    <option key={t} value={t}>
                        {t}
                    </option>
                ))}
            </select>

            <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
            />

            <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
            >
                <option value="food">Food</option>
                <option value="transport">Transport</option>
                <option value="hotel">Hotel</option>
                <option value="activities">Activities</option>
            </select>

            <button type="submit">Add</button>
        </form>
    );
}