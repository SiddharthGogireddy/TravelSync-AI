import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getTrip } from "../services/api";

export default function LoadTrip() {
    const [tripId, setTripId] = useState("");
    const [error, setError] = useState("");
    const navigate = useNavigate();

    const handleLoadTrip = async () => {
        if (!tripId.trim()) {
            setError("Please enter a Trip ID");
            return;
        }

        try {
            setError("");

            await getTrip(tripId.trim());

            navigate(`/trip/${tripId.trim()}`);
        } catch {
            setError("Trip not found");
        }
    };

    return (
        <div className="page">
            <div className="card">
                <h2>Load Saved Trip</h2>

                <input
                    type="text"
                    placeholder="Enter Trip ID"
                    value={tripId}
                    onChange={(e) =>
                        setTripId(e.target.value)
                    }
                />

                <button onClick={handleLoadTrip}>
                    Load Trip
                </button>

                {error && (
                    <p>{error}</p>
                )}
            </div>
        </div>
    );
}