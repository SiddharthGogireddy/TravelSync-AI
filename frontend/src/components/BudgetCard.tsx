import "./BudgetCard.css";
import { formatCurrency } from "../services/currency";

type BudgetProps = {
  budget: {
    total_budget: number;
    estimated_cost: number;
    remaining: number;
    average_per_day: number;
    average_per_person: number;
    status: string;
    currency?: string;
  };
  displayCurrency?: string;
  originalCurrency?: string;
  formatAmount?: (amount: number) => string;
};

export default function BudgetCard({
  budget,
  displayCurrency,
  originalCurrency,
  formatAmount,
}: BudgetProps) {
  const safeBudget = {
    total_budget: budget?.total_budget ?? 0,
    estimated_cost: budget?.estimated_cost ?? 0,
    remaining: budget?.remaining ?? 0,
    average_per_day: budget?.average_per_day ?? 0,
    average_per_person: budget?.average_per_person ?? 0,
    status: budget?.status ?? "Within Budget",
  };

  const origCurr = originalCurrency || budget?.currency || "INR";
  const dispCurr = displayCurrency || origCurr;
  const isConverted = dispCurr !== origCurr;

  const renderValue = (val: number) => {
    if (formatAmount) {
      return formatAmount(val);
    }
    if (displayCurrency) {
      return formatCurrency(val, displayCurrency);
    }
    return `₹${val.toLocaleString()}`;
  };

  return (
    <div className="budget-card">
      <div className="budget-grid">
        <div className="budget-item">
          <span>Total Budget</span>
          <h3>{renderValue(safeBudget.total_budget)}</h3>
          {isConverted && (
            <small style={{ color: "#64748b", fontSize: "0.72rem" }}>
              Orig: {formatCurrency(safeBudget.total_budget, origCurr)}
            </small>
          )}
        </div>

        <div className="budget-item">
          <span>Estimated Cost</span>
          <h3>{renderValue(safeBudget.estimated_cost)}</h3>
          {isConverted && (
            <small style={{ color: "#64748b", fontSize: "0.72rem" }}>
              Orig: {formatCurrency(safeBudget.estimated_cost, origCurr)}
            </small>
          )}
        </div>

        <div className="budget-item">
          <span>Remaining</span>
          <h3>{renderValue(safeBudget.remaining)}</h3>
          {isConverted && (
            <small style={{ color: "#64748b", fontSize: "0.72rem" }}>
              Orig: {formatCurrency(safeBudget.remaining, origCurr)}
            </small>
          )}
        </div>

        <div className="budget-item">
          <span>Average / Day</span>
          <h3>{renderValue(safeBudget.average_per_day)}</h3>
        </div>

        <div className="budget-item">
          <span>Average / Person</span>
          <h3>{renderValue(safeBudget.average_per_person)}</h3>
        </div>

        <div className="budget-item">
          <span>Status</span>
          <h3>{safeBudget.status}</h3>
        </div>
      </div>

      {isConverted && (
        <div
          style={{
            marginTop: 12,
            padding: "6px 12px",
            background: "#f1f5f9",
            borderRadius: 6,
            fontSize: "0.74rem",
            color: "#64748b",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>
            ℹ️ Indicative exchange rate conversion ({origCurr} → {dispCurr}). Bank or card provider rates may vary.
          </span>
          <span>Source currency: {origCurr}</span>
        </div>
      )}
    </div>
  );
}