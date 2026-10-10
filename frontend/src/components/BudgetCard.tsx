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
  const safeBudget = {
    total_budget: budget?.total_budget ?? 0,
    estimated_cost: budget?.estimated_cost ?? 0,
    remaining: budget?.remaining ?? 0,
    average_per_day: budget?.average_per_day ?? 0,
    average_per_person: budget?.average_per_person ?? 0,
    status: budget?.status ?? "Within Budget",
  };

  return (
    <div className="budget-card">
      

      <div className="budget-grid">
        <div className="budget-item">
          <span>Total Budget</span>
          <h3>₹{safeBudget.total_budget.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Estimated Cost</span>
          <h3>₹{safeBudget.estimated_cost.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Remaining</span>
          <h3>₹{safeBudget.remaining.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Average / Day</span>
          <h3>₹{safeBudget.average_per_day.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Average / Person</span>
          <h3>₹{safeBudget.average_per_person.toLocaleString()}</h3>
        </div>

        <div className="budget-item">
          <span>Status</span>
          <h3>{safeBudget.status}</h3>
        </div>
      </div>
    </div>
  );
}