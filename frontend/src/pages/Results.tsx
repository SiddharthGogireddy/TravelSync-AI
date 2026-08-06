import ReactMarkdown from "react-markdown";
import SummaryCard from "../components/SummaryCard";
import HotelCard from "../components/HotelCard";
import WeatherCard from "../components/WeatherCard";
import DayCard from "../components/DayCard";
import type { Summary, Place, Weather, Hotel } from "../types/trip";

interface Props {
    data: {
        summary: Summary;
        trip: {
            weather: Weather[];
            hotels: Hotel[];
            day_schedule: Record<string, Place[]>;
        };
        itinerary: {
            itinerary: string;
        };
    };
}

export default function Result({ data }: Props) {

    if (!data) {
        return <h2>No itinerary found.</h2>;
    }

    const { summary, trip, itinerary } = data;

    return (

        <div className="result">

            <SummaryCard summary={summary} />

            <h2>Weather</h2>

          {trip.weather.map((day: Weather, index: number) => (
    <WeatherCard
        key={index}
        weather={day}
    />
))}
            <h2>Hotels</h2>
            {trip.hotels.map((hotel: Hotel, index: number) => (
                <HotelCard
                    key={index}
                    hotel={hotel}
                />
            ))}

            <h2>Daily Attractions</h2>

            {Object.entries(trip.day_schedule).map(
                ([day, places]: [string, Place[]]) => (

                    <DayCard
                        key={day}
                        day={day}
                        places={places}
                    />

                )
            )}

            <h2>AI Itinerary</h2>

            <ReactMarkdown>

                {itinerary.itinerary}

            </ReactMarkdown>

        </div>

    );

}