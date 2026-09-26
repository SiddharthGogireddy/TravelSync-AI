import { useState } from "react";

interface Props {
    tripId: string;
}

export default function ExpenseTracker({ tripId }: Props) {
    const [title, setTitle] = useState("");
    const [amount, setAmount] = useState("");
    const [paidBy, setPaidBy] = useState("");
    const [category, setCategory] = useState("food");

    async function handleAddExpense() {
        if (!title || !amount || !paidBy) {
            return;
        }

        const response = await fetch(
            "http://127.0.0.1:8000/expense/",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    trip_id: tripId,
                    expense: {
                        title,
                        amount: Number(amount),
                        paid_by: paidBy,
                        category,
                    },
                }),
            }
        );

        if (!response.ok) {
            console.error("Failed to add expense");
            return;
        }

        setTitle("");
        setAmount("");
    }

    return (
        <div className="expense-tracker">
            <h2>Expenses</h2>

            <input
                type="text"
                placeholder="Expense title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
            />

            <input
                type="number"
                placeholder="Amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
            />

            <input
                type="text"
                placeholder="Paid by"
                value={paidBy}
                onChange={(e) => setPaidBy(e.target.value)}
            />

            <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
            >
                <option value="food">Food</option>
                <option value="hotel">Hotel</option>
                <option value="transport">Transport</option>
                <option value="activities">Activities</option>
                <option value="emergency">Emergency</option>
                <option value="other">Other</option>
            </select>

            <button onClick={handleAddExpense}>
                Add Expense
            </button>
        </div>
    );
}