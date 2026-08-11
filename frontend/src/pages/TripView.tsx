import { useEffect, useState } from "react";
import Dashboard from "../components/Dashboard";
import WeatherCard from "../components/WeatherCard";
import HotelCard from "../components/HotelCard";
import DayCard from "../components/DayCard";

import {
    type TripApiResponse,
    type Weather,
    type Hotel,
    type Traveler  
} from "../types/api";

function getTripIdFromUrl(): string | undefined {
    if (typeof window === "undefined") return undefined;
    const match = window.location.pathname.match(/\/trip\/([^/]+)/);
    return match?.[1];
}
export default function TripView() {
    const [data, setData] = useState<TripApiResponse | null>(null);

    useEffect(() => {
        const tripId = getTripIdFromUrl();
        if (!tripId) return;

        async function fetchTrip() {
            try {
                const res = await fetch(`http://127.0.0.1:8000/trip/${tripId}`);
                const json: TripApiResponse = await res.json();
                setData(json);
            } catch (err) {
                console.error(err);
            }
        }

        fetchTrip();
    }, []);

    if (!data) return <div>Loading...</div>;

    const { dashboard, trip, itinerary } = data;

    // ✅ Normalize weather safely
    const normalizedWeather: Weather[] = trip.weather.map((w) => ({
        ...w,
        description: w.description ?? "",
    }));

    return (
        <div style={{ padding: "20px" }}>

            {/* Dashboard */}
            <Dashboard dashboard={dashboard} />

            {/* Travelers */}
            <h2>Travelers</h2>
            {trip.travelers.map((t: Traveler, i: number) => (
                <div key={i}>
                    <b>{t.name}</b> — {t.budget}
                </div>
            ))}

            {/* Weather */}
            <h2>Weather</h2>
            {normalizedWeather.map((day: Weather, index: number) => (
                <WeatherCard key={index} weather={day} />
            ))}

            {/* Hotels */}
            <h2>Hotels</h2>
            {trip.hotels.map((hotel: Hotel, index: number) => (
                <HotelCard key={index} hotel={hotel} />
            ))}

            {/* Daily Plan */}
            <h2>Daily Plan</h2>
            {Object.entries(trip.day_schedule).map(([day, places]) => (
                <DayCard key={day} day={day} places={places} />
            ))}
            {/* AI Itinerary */}
            <h2>AI Itinerary</h2>
            <pre style={{ whiteSpace: "pre-wrap" }}>
                {itinerary.itinerary}
            </pre>

        </div>
    );
}