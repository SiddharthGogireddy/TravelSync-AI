type Props = {
    total: number;
};

export default function ExpenseCard({
    total,
}: Props) {

    return (
        <div
            style={{
                background: "white",
                padding: 20,
                borderRadius: 12,
                boxShadow:
                    "0 2px 8px rgba(0,0,0,.15)",
            }}
        >
            <h2>Total Expenses</h2>

            <h1>
                ₹{total.toLocaleString()}
            </h1>
        </div>
    );
}