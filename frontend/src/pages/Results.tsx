import { useState } from "react";

import Dashboard from "../components/Dashboard";
import BudgetCard from "../components/BudgetCard";
import MapView from "../components/MapView";

import type {
    TripResponse,
    Place,
} from "../types/api";

import type { Expense } from "../types/expense";

interface Props {
    data: TripResponse;
}

export default function Results({ data }: Props) {
    const [expenses] =
        useState<Expense[]>([]);

    const [selectedPlace] =
        useState<Place | null>(null);

    if (!data?.trip) {
        return <div>No trip data available.</div>;
    }

    const trip = data.trip;

    const dashboard = data.dashboard;

    const itinerary = data.itinerary;

    const total = expenses.reduce(
        (sum, expense) =>
            sum + expense.amount,
        0
    );

    const schedule:
        Record<string, Place[]> =
        trip.day_schedule ?? {};

    return (
        <div
            style={{
                padding: 20,
            }}
        >
            <h1>Trip Results</h1>

            {dashboard && (
                <Dashboard
                    dashboard={dashboard}
                />
            )}

            <br />

            <BudgetCard
                budget={trip.budget}
            />

            <hr />

            <h2>Travelers</h2>

            {trip.travelers.map(
                (traveler, index) => (
                    <div key={index}>
                        {traveler.name}
                        {" — "}
                        ₹{traveler.budget}
                    </div>
                )
            )}

            <hr />

            <h2>Weather</h2>

            {trip.weather.map(
                (weather, index) => (
                    <div key={index}>
                        {weather.date}
                        {" — "}
                        {weather.max_temp}°
                        {" / "}
                        {weather.min_temp}°
                    </div>
                )
            )}

            <hr />

            <h2>Hotels</h2>

            {trip.hotels.map(
                (hotel, index) => (
                    <div key={index}>
                        {hotel.name}
                        {" — "}
                        {hotel.distance_km} km
                    </div>
                )
            )}

            <hr />

            <h2>Daily Plan</h2>

            {Object.entries(schedule).map(
                ([day, places]) => (
                    <div key={day}>
                        <h3>{day}</h3>

                        {places.map(
                            (
                                place,
                                index
                            ) => (
                                <div
                                    key={index}
                                >
                                    {place.name}
                                    {" ("}
                                    {
                                        place.category
                                    }
                                    {")"}
                                </div>
                            )
                        )}
                    </div>
                )
            )}

            <hr />

            <h2>Map</h2>

            <MapView
                lat={
                    trip
                        .destination_location
                        .lat
                }
                lon={
                    trip
                        .destination_location
                        .lon
                }
                places={trip.places}
                hotels={trip.hotels}
                selectedPlace={
                    selectedPlace
                }
            />

            <h2>Total Expenses</h2>

            <p>₹{total}</p>

            <hr />

            <h2>AI Itinerary</h2>

            <pre>
                {JSON.stringify(
                    itinerary,
                    null,
                    2
                )}
            </pre>
        </div>
    );
}