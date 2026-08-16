import { useEffect, useState } from "react";
import AddExpenseModal from "../components/AddExpenseModal";
import { addExpense } from "../services/expense";
import Dashboard from "../components/Dashboard";
import WeatherCard from "../components/WeatherCard";
import type{ Place } from "../types/api";
import DayCard from "../components/DayCard";
import MapView from "../components/MapView";
import BudgetCard from "../components/BudgetCard";
import BudgetBreakdown from "../components/BudgetBreakdown";
import BudgetStatus from "../components/BudgetStatus";
import BudgetPieChart from "../components/BudgetPieChart";

import ExpenseCard from "../components/ExpenseCard";
import ExpenseTable from "../components/ExpenseTable";
import SettlementCard from "../components/SettlementCard";

import { getExpenses } from "../services/expense";

import type {
    TripResponse,
    Weather,

    Traveler,
} from "../types/api";

import type {
    ExpenseResponse,
} from "../types/expense";

function getTripIdFromUrl(): string | undefined {
    if (typeof window === "undefined") return undefined;

    const match = window.location.pathname.match(
        /\/trip\/([^/]+)/
    );

    return match?.[1];
}

export default function TripView() {
    async function handleAddExpense(
    title: string,
    amount: number,
    paidBy: string
) {
    
    const tripId = getTripIdFromUrl();

    if (!tripId) return;

    await addExpense(
        tripId,
        {
            title,
            amount,
            paid_by: paidBy,
        }
    );

    const updated =
        await getExpenses(tripId);

    setExpenseData(updated);

}   const [ selectedPlace,setSelectedPlace] =
    useState<Place | null>(null);
    const [data, setData] =
        useState<TripResponse | null>(null);

    const [expenseData, setExpenseData] =
        useState<ExpenseResponse | null>(null);

    useEffect(() => {

        const tripId = getTripIdFromUrl();

        if (!tripId) return;

        async function fetchTrip(id: string) {

            try {

                const res = await fetch(
                    `http://127.0.0.1:8000/trip/${id}`
                );

                const json: TripResponse =
                    await res.json();

                setData(json);

                const expenses =
                    await getExpenses(id);

                setExpenseData(expenses);

            }

            catch (err) {

                console.error(err);

            }

        }

        fetchTrip(tripId);

    }, []);

    if (!data)
        return <div>Loading...</div>;

    const { dashboard, trip } = data;
    

    const normalizedWeather: Weather[] =
        trip.weather.map((w) => ({
            ...w,
            description:
                w.description ?? "",
        }));

    return (
        
        <div
            style={{
                maxWidth: "1200px",
                margin: "0 auto",
                padding: "20px",
            }}
        >

            <Dashboard dashboard={dashboard} />

            <br />

            <BudgetCard
                budget={trip.budget}
            />

            <br />

            <BudgetStatus
                status={trip.budget.status}
            />

            <br />

            <BudgetBreakdown
                categories={
                    trip.budget.categories
                }
            />

            <br />

            <BudgetPieChart
                categories={
                    trip.budget.categories
                }
            />

            <hr />

            <h2> Travelers</h2>

            {trip.travelers.map(
                (traveler: Traveler, index: number) => (

                    <div key={index}>

                        <b>{traveler.name}</b>

                        {" - "}

                        {traveler.budget}

                    </div>

                )
            )}

            <hr />

            <h2> Weather</h2>

            {normalizedWeather.map(
                (weather: Weather, index) => (

                    <WeatherCard
                        key={index}
                        weather={weather}
                    />

                )
            )}

            <hr />

            <h2> Hotels</h2>

            {trip.hotels.map((hotel, index) => (
    <div key={index}>
        <a
            href={`https://www.google.com/maps?q=${hotel.lat},${hotel.lon}`}
            target="_blank"
            rel="noreferrer"
        >
            {hotel.name}
        </a>
    </div>
))}

            <hr />

            <h2> Daily Plan</h2>

            {trip.day_schedule &&
    Object.entries(trip.day_schedule).map(
        ([day, places]) => (
            <DayCard
                key={day}
                day={day}
                places={places}
                onSelect={setSelectedPlace}
            />
        )
    )}
     
            <hr />

            <h2>AI Itinerary</h2>

{data.itinerary?.days?.map((day) => (
    <div
        key={day.day}
        style={{
            border: "1px solid lightgray",
            padding: "16px",
            marginBottom: "16px",
            borderRadius: "10px",
        }}
    >
        <h3>
            Day {day.day}: {day.title}
        </h3>

        <h4>Activities</h4>

        <ul>
            {day.activities.map(
                (activity, index) => (
                    <li key={index}>
                        {activity}
                    </li>
                )
            )}
        </ul>

        <h4>Food</h4>

        <ul>
            {day.food.map(
                (food, index) => (
                    <li key={index}>
                        {food}
                    </li>
                )
            )}
        
        </ul>
        <h2> Map</h2>
            <MapView
    lat={trip.destination_location.lat}
    lon={trip.destination_location.lon}
    places={trip.places}
    hotels={trip.hotels}
    selectedPlace={selectedPlace}
/>
        <p>
            <b>Budget:</b> {day.budget}
        </p>
    </div>
))}

            <hr />
                <AddExpenseModal
    travelers={
        trip.travelers.map(
            (traveler) => traveler.name
        )
    }
    onAdd={handleAddExpense}
/>
            <h2> Trip Expenses</h2>

            {expenseData && (

                <>

                    <ExpenseCard
                        total={
                            expenseData.expenses.reduce(
                                (
                                    sum,
                                    expense
                                ) =>
                                    sum +
                                    expense.amount,
                                0
                            )
                        }
                    />

                    <br />

                    <ExpenseTable
                        expenses={
                            expenseData.expenses
                        }
                    />

                    <br />

                    <SettlementCard
                        settlements={
                            expenseData.settlements
                        }
                    />

                </>

            )}

        </div>
        

    );

}