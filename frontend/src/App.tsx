import { useState } from "react";
import { BrowserRouter, Routes, Route, } from "react-router-dom";

import TripForm from "./components/TripForm";
import Results from "./pages/Results";

import TripView from "./pages/TripView";

import { generateTrip } from "./services/api";

import type { TripRequest } from "./types/trip";
import type { TripResponse } from "./types/api";

export default function App() {
    const [data, setData] = useState<TripResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const handleSubmit = async (
    formData: TripRequest
) => {
    try {
        setLoading(true);

        const result =
            await generateTrip(formData);

        console.log(
            "Trip generated:",
            result
        );

        if (result.trip_id) {
            window.location.href =
                `/trip/${result.trip_id}`;

            return;
        }

        setData(result);
    }

    catch (err) {
        console.error(err);
    }

    finally {
        setLoading(false);
    }
};

    return (
        <BrowserRouter>
           <div>
                <Routes>
                    <Route
                        path="/"
                        element={
                            <>
                                <h1
                                    style={{
                                        textAlign: "center",
                                        marginBottom: "20px",
                                    }}
                                >
                                    TravelSync AI
                                </h1>

                                 <div style={{ marginBottom: "40px" }}>
        <TripForm onSubmit={handleSubmit} />
    </div>

                                {loading && <p>Loading...</p>}

                                {data && <Results data={data} />}
                            </>
                        }
                    />

                    <Route path="/trip/:id" element={<TripView />} />
                </Routes>
            </div>
        </BrowserRouter>
    );
}