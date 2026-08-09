
import BudgetCard from "../components/BudgetCard";
import Dashboard from "../components/Dashboard";
import type { Expense, Settlement } from "../types/expense";
import type { TripApiResponse, Place } from "../types/api";
import { useState } from "react";
import ExpenseDashboard from "../components/ExpenseDashboard";
import ExpenseForm from "../components/ExpenseForm";
import ExpenseCharts from "../components/ExpenseCharts";
import ExpenseTable from "../components/ExpenseTable";
interface Props {
    data: TripApiResponse;
}
export default function Results({ data }: Props) {
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [balances] = useState<Record<string, number>>({});
    const settlements = settleDebts(balances);

<h2>Settlements</h2>
{settlements.map((s, i) => (
    <div key={i}>
        {s.from} pays ₹{s.amount.toFixed(2)} to {s.to}
    </div>
))}
    const handleDelete = (index: number): void => {
        setExpenses((prev) => prev.filter((_, i) => i !== index));
    };
function settleDebts(balances: Record<string, number>): Settlement[] {
    const creditors: [string, number][] = [];
    const debtors: [string, number][] = [];

    Object.entries(balances).forEach(([name, amt]) => {
        if (amt > 0) creditors.push([name, amt]);
        else if (amt < 0) debtors.push([name, -amt]);
    });

    const settlements: Settlement[] = [];

    let i = 0, j = 0;

    while (i < debtors.length && j < creditors.length) {
        const [dName, dAmt] = debtors[i];
        const [cName, cAmt] = creditors[j];

        const pay = Math.min(dAmt, cAmt);

        settlements.push({
            from: dName,
            to: cName,
            amount: pay,
        });

        debtors[i][1] -= pay;
        creditors[j][1] -= pay;

        if (debtors[i][1] === 0) i++;
        if (creditors[j][1] === 0) j++;
    }

    return settlements;
}
    const dashboard = data.dashboard;
    const trip = data.trip;
    const itinerary = data.itinerary;
    const travelerNames = trip.travelers?.map(t => t.name) ?? [];
    // ✅ SAFE fallback (trip_id may not exist)
    const shareUrl = `${window.location.origin}/trip/demo`;

    // ✅ SAFE schedule typing
    const schedule: Record<string, Place[]> =
        trip?.day_schedule ?? {};
    const normalizedBudget = {
    total_budget: trip.budget?.total ?? 0,
    estimated_cost: trip.budget?.estimated ?? 0,
    remaining:
        (trip.budget?.total ?? 0) -
        (trip.budget?.estimated ?? 0),

    categories: {
        hotel: trip.budget?.hotel ?? 0,
        food: trip.budget?.food ?? 0,
        transport: trip.budget?.transport ?? 0,
        activities: trip.budget?.activities ?? 0,
        emergency: trip.budget?.emergency ?? 0,
    },

    per_person: trip.travelers?.map((t) => ({
        name: t.name,
        amount: Number(t.budget) || 0,
    })) ?? [],
};
const total = expenses.reduce((sum, e) => sum + e.amount, 0);
const travelerBudgets = trip.travelers?.map((t) => ({
    name: t.name,
    amount: Number(t.budget) || 0,
})) ?? [];
    return (
        <div style={{ padding: 20 }}>
            
            <BudgetCard budget={normalizedBudget} />
            {/* Dashboard */}
            {dashboard && <Dashboard dashboard={dashboard} />}
            <ExpenseForm
    travelers={travelerNames}
    onAdd={(e) =>
        setExpenses((prev) => [...prev, e])
    }
/>
    <ExpenseCharts expenses={expenses} />
<ExpenseDashboard expenses={expenses} budgets={travelerBudgets} />
            {/* Share */}
            <div>
                <h3>Share</h3>
                <input value={shareUrl} readOnly />
            </div>
            <ExpenseTable
    expenses={expenses}
    onDelete={handleDelete}
/>
            {/* Travelers */}
            <h2>Travelers</h2>
            {trip?.travelers?.map((t, i) => (
                <div key={i}>
                    {t?.name ?? "Unknown"} — ₹{t?.budget ?? 0}
                </div>
            ))}

            {/* Weather */}
            <h2>Weather</h2>
            {trip?.weather?.map((w, i) => (
                <div key={i}>
                    {w?.date ?? "N/A"} — {w?.max_temp ?? 0}° / {w?.min_temp ?? 0}°
                </div>
            ))}

            {/* Hotels */}
            <h2>Hotels</h2>
            {trip?.hotels?.map((h, i) => (
                <div key={i}>
                    {h?.name ?? "Hotel"} — {h?.distance ?? 0} km
                </div>
            ))}

            {/* Daily Plan */}
            <h2>Daily Plan</h2>
            {Object.entries(schedule).map(([day, places]) => (
                <div key={day}>
                    <h3>{day}</h3>

                    {(places ?? []).map((p, i) => (
                        <div key={i}>
                            {p?.name ?? "Place"} (
                            {p?.type ?? p?.category ?? "General"})
                        </div>
                    ))}
                </div>
            ))}
            <h4>Total Spent: ₹{total}</h4>
            {/* Itinerary */}
            <h2>AI Itinerary</h2>
            <div style={{ whiteSpace: "pre-wrap" }}>
                {itinerary?.itinerary ?? ""}
            </div>
        </div>
    );
}