import { useState } from "react";
import TripForm from "./components/TripForm";
import Results from "./pages/Results";
import { generateTrip } from "./services/api";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { TripView } from "./pages/TripView";
import type { Dashboard, Summary, Budget, Weather, Hotel, Place,TripRequest, BestTime } from "./types/trip";
import Home from "./pages/Home";
export default function App() {
    type ApiResponse = {
    trip_id: string;
    summary: Summary;
    dashboard: Dashboard;
    trip: {
        budget: Budget;
        weather: Weather[];
        hotels: Hotel[];
        day_schedule: Record<string, Place[]>;
        travelers: {
            name: string;
            budget: string;
            interests: string[];
            pace: string;
        }[];
        best_time:BestTime;
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
            <BrowserRouter>
    <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/trip/:id" element={<TripView data={data} />} />
    </Routes>
</BrowserRouter>
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