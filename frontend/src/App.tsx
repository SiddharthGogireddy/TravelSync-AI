import { useState } from "react";
import TripForm from "./components/TripForm";
import Results from "./pages/Results";
import { generateTrip } from "./services/api";
import type { Dashboard, Summary, Budget, Weather, Hotel, Place,TripRequest } from "./types/trip";
export default function App() {
    type ApiResponse = {
    summary: Summary;
    dashboard: Dashboard;
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
    const [data, setData] = useState<ApiResponse | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (formData: TripRequest) => {

        setLoading(true);

        const result = await generateTrip(formData);

        setData(result);

        setLoading(false);
    };

    return (
        <div style={{ 
          maxWidth: "1100px",
            margin: "auto",
            padding: "20px",
            fontFamily: "Arial"
         }}>

            <h1 style={{
                textAlign: "center",
                marginBottom: "20px"
            }}>
                TravelSync AI
            </h1>

            <TripForm onSubmit={handleSubmit} />

            {loading && <p>Loading...</p>}

            {data && <Results data={data} />}

        </div>
    );
}