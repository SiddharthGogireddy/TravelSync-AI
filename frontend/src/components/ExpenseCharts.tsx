import {
    PieChart, Pie, Cell, Tooltip,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from "recharts";

import type { Expense } from "../types/expense";

interface Props {
    expenses: Expense[];
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042"];

export default function ExpenseCharts({ expenses }: Props) {

    // ✅ Category aggregation
    const categoryMap: Record<string, number> = {};
    expenses.forEach((e) => {
        categoryMap[e.category] =
            (categoryMap[e.category] || 0) + e.amount;
    });

    const categoryData = Object.entries(categoryMap).map(
        ([name, value]) => ({ name, value })
    );

    // ✅ Traveler aggregation
    const travelerMap: Record<string, number> = {};
    expenses.forEach((e) => {
        travelerMap[e.paid_by] =
            (travelerMap[e.paid_by] || 0) + e.amount;
    });

    const travelerData = Object.entries(travelerMap).map(
        ([name, value]) => ({ name, value })
    );

    return (
        <div style={{ display: "flex", gap: "40px", flexWrap: "wrap" }}>

            {/* Category Breakdown */}
            <div>
                <h3>Category Breakdown</h3>
                <PieChart width={300} height={300}>
                    <Pie
                        data={categoryData}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={100}
                    >
                        {categoryData.map((_, index) => (
                            <Cell key={index} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip />
                </PieChart>
            </div>

            {/* Spending per Traveler */}
            <div>
                <h3>Spending per Traveler</h3>
                <BarChart width={400} height={300} data={travelerData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value" fill="#82ca9d" />
                </BarChart>
            </div>

        </div>
    );
}