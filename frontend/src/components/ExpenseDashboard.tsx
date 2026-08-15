import type { Expense } from "../types/expense";

interface TravelerBudget {
    name: string;
    amount: number;
}

interface Props {
    expenses: Expense[];
    budgets: TravelerBudget[];
}

export default function ExpenseDashboard({ expenses, budgets }: Props) {

    // ✅ calculate spent per traveler
    const spent: Record<string, number> = {};

    expenses.forEach((e) => {
        spent[e.paid_by] =
    (spent[e.paid_by] || 0) + e.amount;
        });

    return (
        <div>
            <h3>Expense Summary</h3>

            {budgets.map((b) => {
                const used = spent[b.name] || 0;
                const remaining = b.amount - used;

                return (
                    <div key={b.name}>
                        <b>{b.name}</b> <br />
                        Budget: ₹{b.amount} <br />
                        Spent: ₹{used} <br />
                        Remaining: ₹{remaining}
                        <hr />
                    </div>
                );
            })}
        </div>
    );
}