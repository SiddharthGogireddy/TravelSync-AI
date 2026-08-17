import { useState } from "react";
import type { TripRequest } from "../types/trip";

export default function TripForm({
    onSubmit,
}: {
    onSubmit: (data: TripRequest) => void;
}) {
    const [source, setSource] = useState("");
    const [destination, setDestination] = useState("");
    const [days, setDays] = useState(3);

    const [name, setName] = useState("");
    const [budget, setBudget] = useState("Medium");
    const [travelMode, setTravelMode] = useState<
        "car" | "bus" | "train" | "flight"
    >("car");

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        onSubmit({
            source,
            destination,
            days,
            travelers: [
                {
                    name,
                    interests: ["Beaches"],
                    budget,
                    pace: "Balanced",
                },
            ],
            mandatory_visits: [],
            travel_mode: travelMode,
        });
    };

    return (
        <form className="card" onSubmit={handleSubmit}>
            <h2>Plan Your Trip</h2>

            <input
                placeholder="Your Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
            />

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

            <label>Days</label>

<input
    type="number"
    value={days || ""}
    onChange={(e) => setDays(Number(e.target.value))}
/>

            <select
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
            >
                <option>Low</option>
                <option>Medium</option>
                <option>High</option>
            </select>

            <select
                value={travelMode}
                onChange={(e) =>
                    setTravelMode(
                        e.target.value as
                            | "car"
                            | "bus"
                            | "train"
                            | "flight"
                    )
                }
            >
                <option value="car">Car</option>
                <option value="bus">Bus</option>
                <option value="train">Train</option>
                <option value="flight">Flight</option>
            </select>

            <button
                style={{
                    marginTop: 10,
                    padding: 10,
                    background: "#4caf50",
                    color: "white",
                    border: "none",
                    borderRadius: 6,
                }}
            >
                Plan Trip
            </button>
        </form>
    );
}