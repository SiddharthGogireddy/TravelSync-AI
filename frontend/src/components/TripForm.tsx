import { useState } from "react";
import type { TripRequest } from "../types/trip";
export default function TripForm({ onSubmit }: { onSubmit: (data: TripRequest) => void }) {

    const [source, setSource] = useState<string>("");
    const [destination, setDestination] = useState<string>("");
    const [days, setDays] = useState<number>(3);

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
       <form className="card" onSubmit={handleSubmit}>

    <h2>Plan Your Trip</h2>

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
        placeholder="Number of Days"
        value={days}
        onChange={(e) => setDays(Number(e.target.value))}
    />

    <button style={{
        marginTop: 10,
        padding: 10,
        background: "#4caf50",
        color: "white",
        border: "none",
        borderRadius: 6
    }}>
        Plan Trip
    </button>

</form>
        
    );
}