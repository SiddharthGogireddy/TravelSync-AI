import Dashboard from "../components/Dashboard";
import BudgetCard from "../components/BudgetCard";

import type {
    Dashboard as DashboardType,
    Summary,
    Budget,
    Weather,
    Hotel,
    Place
} from "../types/trip";

interface Props {
    data: {
        summary: Summary;
        dashboard: DashboardType;
        trip: {
            budget: Budget;
            weather: Weather[];
            hotels: Hotel[];
            day_schedule: Record<string, Place[]>;
        };
        itinerary: {
            itinerary: string;
        };
    };
}

export default function Results({ data }: Props) {

    if (!data) return <div>Loading...</div>;

    const { dashboard, trip, itinerary } = data;

    return (
        <div style={{ padding: 20 }}>

            {/* Dashboard */}
            {dashboard && (
                <Dashboard dashboard={dashboard} />
            )}

            {/* Budget */}
            {trip?.budget && (
                <BudgetCard budget={trip.budget} />
            )}

            {/* Weather */}
            <h2>Weather</h2>
            {trip.weather.map((day: Weather, index: number) => (
                <div key={index}>
                    {day.date} — {day.max_temp}°C / {day.min_temp}°C
                </div>
            ))}

            {/* Hotels */}
            <h2>Hotels</h2>
            {trip.hotels.map((hotel: Hotel, index: number) => (
                <div key={index}>
                    {hotel.name} — {hotel.distance_km} km
                </div>
            ))}

            {/* Day Schedule */}
            <h2>Daily Plan</h2>
            {Object.entries(trip.day_schedule).map(
                ([day, places]: [string, Place[]]) => (
                    <div key={day}>
                        <h3>Day {day}</h3>

                        {places.map((place: Place, i: number) => (
                            <div key={i}>
                                {place.name} ({place.category})
                            </div>
                        ))}
                    </div>
                )
            )}

            {/* Itinerary */}
            <h2>AI Itinerary</h2>
            <div style={{
    whiteSpace: "pre-wrap",
    lineHeight: 1.6
}}>
    {itinerary.itinerary}
</div>

        </div>
    );
}