import { useEffect, useState } from "react";
import ExpenseCard from "../components/ExpenseCard";
import ExpenseTable from "../components/ExpenseTable";
import SettlementCard from "../components/SettlementCard";
import {
    getExpenses,
} from "../services/expense";

import type {
    ExpenseResponse,
} from "../types/expense";

export default function ExpenseView() {

    const [data, setData] =
        useState<ExpenseResponse>();
    
    useEffect(() => {

        async function load() {

            const tripId = "YOUR_TRIP_ID";

            const result =
                await getExpenses(tripId);

            setData(result);

        }

        load();

    }, []);

    if (!data)
        return <h2>Loading...</h2>;

    return (
    <div
        style={{
            maxWidth: "1000px",
            margin: "0 auto",
            padding: "20px",
        }}
    >
        <h1> Trip Expenses</h1>

        <ExpenseCard
            total={
                data.expenses.reduce(
                    (sum, expense) => sum + expense.amount,
                    0
                )
            }
        />

        <br />

        <ExpenseTable
            expenses={data.expenses}
        />

        <br />

        <SettlementCard
            settlements={data.settlements}
        />
    </div>
);

}