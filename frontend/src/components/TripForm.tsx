import { useState } from "react";
import type { TripRequest } from "../types/trip";
export default function TripForm({ onSubmit }: { onSubmit: (data: TripRequest) => void }) {

    const [source, setSource] = useState("");
    const [destination, setDestination] = useState("");
    const [days, setDays] = useState(3);

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        onSubmit({
            source,
            destination,
            days,
            travelers: [
                {
                    name: "Siddharth",
                    interests: ["Beaches"],
                    budget: "Medium",
                    pace: "Balanced"
                }
            ],
            mandatory_visits: [],
            travel_mode: "car"
        });
    };

    return (
        <form onSubmit={handleSubmit}>

            <input
                placeholder="Source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
            />

            <input
                placeholder="Destination"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
            />

            <input
                type="number"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
            />

            <button type="submit">
                Plan Trip
            </button>

        </form>
    );
}