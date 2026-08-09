import type { Expense } from "../types/expense";

interface Props {
    expenses: Expense[];
    onDelete: (index: number) => void;
}

export default function ExpenseTable({ expenses, onDelete }: Props) {
    return (
        <div>
            <h3>Expense History</h3>

            {expenses.length === 0 ? (
                <p>No expenses yet</p>
            ) : (
                <table border={1} cellPadding={8}>
                    <thead>
                        <tr>
                            <th>Traveler</th>
                            <th>Amount</th>
                            <th>Category</th>
                            <th>Action</th>
                        </tr>
                    </thead>

                    <tbody>
                        {expenses.map((e, i) => (
                            <tr key={i}>
                                <td>{e.traveler}</td>
                                <td>₹{e.amount}</td>
                                <td>{e.category}</td>
                                <td>
                                    <button onClick={() => onDelete(i)}>
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}