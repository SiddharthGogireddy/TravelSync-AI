import type { BudgetAlert } from "../types/expense";

interface Props {
    alerts: BudgetAlert[];
}

export default function BudgetAlerts({ alerts }: Props) {
    if (alerts.length === 0) {
        return null;
    }

    return (
        <div className="section">
            <h2 className="section-title">
                Budget Alerts
            </h2>

            {alerts.map((alert, index) => (
                <div
                    key={`${alert.category}-${index}`}
                    style={{
                        padding: "12px 16px",
                        marginBottom: "10px",
                        borderRadius: "8px",
                        border: "1px solid #ddd",
                    }}
                >
                    <strong>
                        {alert.category.toUpperCase()}
                    </strong>

                    <p>
                        {alert.message}
                    </p>

                    <small>
                        {alert.percentage_used}% used
                    </small>
                </div>
            ))}
        </div>
    );
}