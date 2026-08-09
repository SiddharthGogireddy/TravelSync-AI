import type { Expense } from "../types/expense";
import { calculateSettlement } from "../services/expenseService";

interface Props {
    expenses: Expense[];
}

export default function ExpenseDashboard({ expenses }: Props) {

    const settlements = calculateSettlement(expenses);

    return (
        <div className="card">
            <h2>Expense Summary</h2>

            {expenses.map((e) => (
                <div key={e.id}>
                    {e.title} — ₹{e.amount} ({e.paidBy})
                </div>
            ))}

            <h3>Settlements</h3>

            {settlements.map((s, i) => (
                <div key={i}>
                    {s.from} pays {s.to} ₹{s.amount}
                </div>
            ))}
        </div>
    );
}