type Props = {
    status: string;
    remaining?: number;
};

export default function BudgetStatus({ status, remaining = 0 }: Props) {
    let color = "#4caf50";
    let message = "Your trip is within budget.";

    if (status === "Near Budget") {
        color = "#ff9800";
        message = "Your trip is close to the budget limit.";
    }

    if (status === "Over Budget") {
        color = "#f44336";
        message = `You are ₹${Math.abs(remaining).toLocaleString()} over budget.`;
    }

    if (status === "Under Budget") {
        message = `You have ₹${remaining.toLocaleString()} remaining.`;
    }

    return (
        <div
            style={{
                background: color,
                color: "white",
                padding: "14px",
                borderRadius: "10px",
                textAlign: "center",
                fontWeight: "bold",
                marginBottom: "15px",
            }}
        >
            <div style={{ fontSize: "18px" }}>
                {status}
            </div>

            <div
                style={{
                    fontSize: "14px",
                    marginTop: "5px",
                    fontWeight: "normal",
                }}
            >
                {message}
            </div>
        </div>
    );
}