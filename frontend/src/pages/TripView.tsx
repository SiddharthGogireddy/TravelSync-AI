import { useEffect, useState } from "react";
import Dashboard from "../components/Dashboard";
import WeatherCard from "../components/WeatherCard";
import HotelCard from "../components/HotelCard";
import DayCard from "../components/DayCard";
import BudgetPieChart
from "../components/BudgetPieChart";
import {
    type TripResponse,
    type Weather,
    type Hotel,
    type Traveler,
    
} from "../types/api";
import BudgetCard from "../components/BudgetCard";
import BudgetBreakdown from "../components/BudgetBreakdown";
import BudgetStatus from "../components/BudgetStatus";
function getTripIdFromUrl(): string | undefined {
    if (typeof window === "undefined") return undefined;
    const match = window.location.pathname.match(/\/trip\/([^/]+)/);
    return match?.[1];
}
export default function TripView() {
    const [data, setData] = useState<TripResponse | null>(null);

    useEffect(() => {
        const tripId = getTripIdFromUrl();
        if (!tripId) return;

        async function fetchTrip() {
            try {
                const res = await fetch(`http://127.0.0.1:8000/trip/${tripId}`);
                const json: TripResponse = await res.json();
                setData(json);
            } catch (err) {
                console.error(err);
            }
        }

        fetchTrip();
    }, []);

    if (!data) return <div>Loading...</div>;

    const { dashboard, trip} = data;


    const normalizedWeather: Weather[] = trip.weather.map((w) => ({
        ...w,
        description: w.description ?? "",
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

        <BudgetCard budget={trip.budget} />

        <br />

        <BudgetStatus
            status={trip.budget.status}
        />

        <br />

        <BudgetBreakdown
            categories={trip.budget.categories}
        />
  
        <BudgetPieChart categories={trip.budget.categories} />

        <hr />

        <h2> Travelers</h2>

        {trip.travelers.map(
            (t: Traveler, i: number) => (
                <div key={i}>
                    <b>{t.name}</b>
                    {" — "}
                    {t.budget}
                </div>
            )
        )}

        <hr />

        <h2> Weather</h2>

        {normalizedWeather.map(
            (day: Weather, index: number) => (
                <WeatherCard
                    key={index}
                    weather={day}
                />
            )
        )}

        <hr />

        <h2> Hotels</h2>

        {trip.hotels.map(
            (hotel: Hotel, index: number) => (
                <HotelCard
                    key={index}
                    hotel={hotel}
                />
            )
        )}

        <hr />

        <h2>🗓 Daily Plan</h2>

        {Object.entries(trip.day_schedule).map(
            ([day, places]) => (
                <DayCard
                    key={day}
                    day={day}
                    places={places}
                />
            )
        )}

        <hr />

        <h2>AI Itinerary</h2>

        <pre
            style={{
                whiteSpace: "pre-wrap",
                background: "#f5f5f5",
                padding: "16px",
                borderRadius: "10px",
            }}
        >
            {trip.itinerary?.itinerary}
        </pre>
    </div>
);

}