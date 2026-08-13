type Expense = {
    title: string;
    amount: number;
    paid_by: string;
};

type Props = {
    expenses: Expense[];
};

export default function ExpenseTable({
    expenses,
}: Props) {

    return (
        <table
            style={{
                width: "100%",
                borderCollapse: "collapse",
            }}
        >
            <thead>
                <tr>
                    <th>Expense</th>
                    <th>Amount</th>
                    <th>Paid By</th>
                </tr>
            </thead>

            <tbody>

                {expenses.map(
                    (expense, index) => (

                        <tr key={index}>

                            <td>{expense.title}</td>

                            <td>
                                ₹{expense.amount}
                            </td>

                            <td>
                                {expense.paid_by}
                            </td>

                        </tr>
                    )
                )}

            </tbody>
        </table>
    );
}