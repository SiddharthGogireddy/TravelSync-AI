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
    console.log("RESULTS COMPONENT IS RUNNING");
    const [expenses] =
        useState<Expense[]>([]);
    const [showItinerary, setShowItinerary] =
    useState(false);
    const [selectedPlace] =
        useState<Place | null>(null);

    if (!data?.trip) {
        return <div>No trip data available.</div>;
    }

    const trip = data.trip;
    console.log("Trip ID:", data.trip_id);
    const dashboard = data.dashboard;

    

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
                  routeCoordinates={
        trip.route_coordinates
                  }
            />

            <h2>Total Expenses</h2>

            <p>₹{total}</p>

    <hr />

<h2>AI Itinerary</h2>

<button
    onClick={() =>
        setShowItinerary(
            !showItinerary
        )
    }
>
    {showItinerary
        ? "Hide Itinerary"
        : "Show Itinerary"}
</button>

<button
    onClick={() =>
        window.open(
            `http://127.0.0.1:8000/trip/${data.trip_id}/pdf`
        )
    }
    style={{
        marginLeft: 10,
    }}
>
    Download PDF
</button>

{showItinerary && (
    <pre>
        {JSON.stringify(
            data.itinerary,
            null,
            2
        )}
    </pre>
)}
            
        </div>
    );
}