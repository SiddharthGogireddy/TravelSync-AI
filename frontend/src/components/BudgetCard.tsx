import "./BudgetCard.css";

type BudgetProps = {
  budget: {
    total_budget: number;
    estimated_cost: number;
    remaining: number;
    average_per_day: number;
    average_per_person: number;
    status: string;
  };
};

export default function BudgetCard({ budget }: BudgetProps) {
  return (
    <div className="budget-card">
      <h2> Budget Overview</h2>

      <div className="budget-grid">
        <div className="budget-item">
          <span>Total Budget</span>
          <h3>₹{budget.total_budget.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Estimated Cost</span>
          <h3>₹{budget.estimated_cost.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Remaining</span>
          <h3>₹{budget.remaining.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Average / Day</span>
          <h3>₹{budget.average_per_day.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Average / Person</span>
          <h3>₹{budget.average_per_person.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Status</span>
          <h3>{budget.status}</h3>
        </div>
      </div>
    </div>
  );
}