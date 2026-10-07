import { useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

import TripForm from "./components/TripForm";
import Results from "./pages/Results";
import LoadTrip from "./pages/LoadTrip";
import TripView from "./pages/TripView";
import TripHistory from "./pages/TripHistory";
import TripComparison from "./pages/TripComparison";
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
                <nav
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        gap: 24,
                        padding: "16px 20px",
                        background: "#fff",
                        borderBottom: "1px solid #e5e7eb",
                        marginBottom: 24,
                    }}
                >
                    <Link
                        to="/"
                        style={{
                            color: "#4f46e5",
                            textDecoration: "none",
                            fontWeight: 600,
                            fontSize: "1rem",
                        }}
                    >
                        Plan Trip
                    </Link>
                    <Link
                        to="/load-trip"
                        style={{
                            color: "#4f46e5",
                            textDecoration: "none",
                            fontWeight: 600,
                            fontSize: "1rem",
                        }}
                    >
                        Load / Restore Trip
                    </Link>
                    <Link
                        to="/trip-history"
                        style={{
                            color: "#4f46e5",
                            textDecoration: "none",
                            fontWeight: 600,
                            fontSize: "1rem",
                        }}
                    >
                        Trip History
                    </Link>
                    <Link
                        to="/compare"
                        style={{
                            color: "#4f46e5",
                            textDecoration: "none",
                            fontWeight: 600,
                            fontSize: "1rem",
                        }}
                    >
                        Compare Trips
                    </Link>
                </nav>
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
<Route
  path="/trip-history"
  element={<TripHistory />}
/>
                    <Route path="/trip/:id" element={<TripView />} />
                    <Route
    path="/load-trip"
    element={<LoadTrip />}
/>
                    <Route
                        path="/compare"
                        element={<TripComparison />}
                    />
                </Routes>
            </div>
        </BrowserRouter>
    );
}