
import "../styles/card.css";

interface BudgetCategory {
    hotel: number;
    food: number;
    transport: number;
    activities: number;
    emergency: number;
}

interface PerPerson {
    name: string;
    amount: number;
}
export interface BudgetView {
    total_budget: number;
    estimated_cost: number;
    remaining: number;
    categories: BudgetCategory;
    per_person: PerPerson[];
}

interface Props {
    budget: BudgetView;
}
export default function BudgetCard({ budget }: Props) {
    return (
        <div>
            <h2>Budget</h2>

            <p>Total: ₹{budget.total_budget}</p>
            <p>Estimated: ₹{budget.estimated_cost}</p>
            <p>Remaining: ₹{budget.remaining}</p>

            <h3>Categories</h3>
            {Object.entries(budget.categories).map(([k, v]) => (
                <div key={k}>
                    {k}: ₹{v}
                </div>
            ))}

            <h3>Per Person</h3>
            {budget.per_person.map((p, i) => (
                <div key={i}>
                    {p.name}: ₹{p.amount}
                </div>
            ))}
        </div>
    );
}