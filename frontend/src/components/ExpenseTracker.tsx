import { useEffect, useState } from "react";
import { getExpenses, addExpense } from "../services/expense";

interface Props {
    tripId: string;
}

interface Expense {
    title: string;
    amount: number;
    paid_by: string;
    category: string;
}

interface Settlement {
    from: string;
    to: string;
    amount: number;
}

interface ExpenseResponse {
    expenses: Expense[];
    balances: Record<string, number>;
    settlements: Settlement[];
    category_totals: Record<string, number>;
    budget_comparison: Record<
        string,
        {
            planned: number;
            actual: number;
            remaining: number;
        }
    >;
}

export default function ExpenseTracker({ tripId }: Props) {
    const [title, setTitle] = useState("");
    const [amount, setAmount] = useState("");
    const [paidBy, setPaidBy] = useState("");
    const [category, setCategory] = useState("food");

    const [expenseData, setExpenseData] =
        useState<ExpenseResponse | null>(null);

    useEffect(() => {
        let isMounted = true;
        async function fetchExpenses() {
            try {
                const data = await getExpenses(tripId);
                if (isMounted) {
                    setExpenseData(data);
                }
            } catch (err: any) {
                console.warn("Failed to load expenses:", err?.message);
            }
        }

        fetchExpenses();
        return () => {
            isMounted = false;
        };
    }, [tripId]);

    async function handleAddExpense() {
        if (!title || !amount || !paidBy) {
            return;
        }

        try {
            await addExpense(tripId, {
                title,
                amount: Number(amount),
                paid_by: paidBy,
                category,
            });

            setTitle("");
            setAmount("");

            const data = await getExpenses(tripId);
            setExpenseData(data);
        } catch (err: any) {
            console.error("Failed to add expense:", err?.message);
        }
    }

    return (
        <div className="expense-tracker">
            <h2>Expenses</h2>

            <input
                type="text"
                placeholder="Expense title"
                value={title}
                onChange={(e) =>
                    setTitle(e.target.value)
                }
            />

            <input
                type="number"
                placeholder="Amount"
                value={amount}
                onChange={(e) =>
                    setAmount(e.target.value)
                }
            />

            <input
                type="text"
                placeholder="Paid by"
                value={paidBy}
                onChange={(e) =>
                    setPaidBy(e.target.value)
                }
            />

            <select
                value={category}
                onChange={(e) =>
                    setCategory(e.target.value)
                }
            >
                <option value="food">Food</option>
                <option value="hotel">Hotel</option>
                <option value="transport">
                    Transport
                </option>
                <option value="activities">
                    Activities
                </option>
                <option value="emergency">
                    Emergency
                </option>
                <option value="other">Other</option>
            </select>

            <button onClick={handleAddExpense}>
                Add Expense
            </button>

            {expenseData && (
                <div>
                    <h3>Added Expenses</h3>

                    {expenseData.expenses.map(
                        (expense, index) => (
                            <div key={index}>
                                <strong>
                                    {expense.title}
                                </strong>
                                {" — ₹"}
                                {expense.amount.toLocaleString()}
                                {" ("}
                                {expense.category}
                                {") — Paid by "}
                                {expense.paid_by}
                            </div>
                        )
                    )}
                </div>
            )}
            {expenseData && (
    <div>
        <h3>Balances</h3>

        {Object.entries(expenseData.balances).map(
            ([name, balance]) => (
                <div key={name}>
                    <strong>{name}</strong>
                    {" : ₹"}
                    {balance.toLocaleString()}
                </div>
            )
        )}
    </div>
)}
        </div>
    );
}