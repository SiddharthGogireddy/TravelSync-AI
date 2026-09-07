import { useState } from "react";
import type { TripRequest } from "../types/trip";
const locations: Record<string, string[]> = {
    India: [
        "Bengaluru, Karnataka, India",
        "Hyderabad, Telangana, India",
        "Chennai, Tamil Nadu, India",
        "Mumbai, Maharashtra, India",
        "Delhi, India",
        "Kolkata, West Bengal, India",
        "Pune, Maharashtra, India",
        "Goa, India",
        "Mysuru, Karnataka, India",
        "Jaipur, Rajasthan, India",
    ],

    Japan: [
        "Tokyo, Japan",
        "Kyoto, Japan",
        "Osaka, Japan",
        "Hiroshima, Japan",
    ],

    "United States": [
        "New York, New York, USA",
        "Los Angeles, California, USA",
        "San Francisco, California, USA",
        "Las Vegas, Nevada, USA",
    ],

    "United Kingdom": [
        "London, England, UK",
        "Edinburgh, Scotland, UK",
        "Manchester, England, UK",
    ],

    France: [
        "Paris, France",
        "Nice, France",
        "Lyon, France",
    ],

    Australia: [
        "Sydney, New South Wales, Australia",
        "Melbourne, Victoria, Australia",
        "Brisbane, Queensland, Australia",
    ],
};

const allLocations: string[] =
    Object.values(locations).flat();
export default function TripForm({
    onSubmit,
}: {
    onSubmit: (data: TripRequest) => void;
}) {
    const [source, setSource] = useState<string>(
    locations.India[0]
);
    const [sourceSelected, setSourceSelected] = useState(true);
const [destinationSelected, setDestinationSelected] = useState(true);
const [destination, setDestination] = useState<string>(
    locations.India[1]
);
    const [days, setDays] = useState(3);
    
    const [name, setName] = useState("");

    const [budget, setBudget] = useState("Medium");

    const [travelMode, setTravelMode] = useState<
        "car" | "bus" | "train" | "flight"
    >("car");

    const handleSubmit = (
    e: React.FormEvent<HTMLFormElement>
) => {
    e.preventDefault();

    if (!sourceSelected || !destinationSelected) {
        alert(
            "Please select a source and destination from the suggestions."
        );
        return;
    }

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
    const [sourceSearch, setSourceSearch] = useState("");
    const [destinationSearch, setDestinationSearch] = useState("");

    const [showSourceResults, setShowSourceResults] = useState(false);
    const [showDestinationResults, setShowDestinationResults] =
    useState(false);
    const filteredSourceLocations = allLocations.filter(
        (location) =>
            location
                .toLowerCase()
                .includes(sourceSearch.toLowerCase())
        );

    const filteredDestinationLocations = allLocations.filter(
        (location) =>
            location
                .toLowerCase()
                .includes(destinationSearch.toLowerCase())
);

    
    return (
        <form
            className="card"
            onSubmit={handleSubmit}
        >
            <h2>Plan Your Trip</h2>

            <div className="form-group">
                <label>Your Name</label>

                <input
                    placeholder="Enter your name"
                    value={name}
                    onChange={(e) =>
                        setName(e.target.value)
                    }
                />
            </div>
                    <div className="form-group location-field">
    <label>Source</label>

                    <input
    placeholder="Search source city..."
    value={sourceSearch}
    onChange={(e) => {
        setSourceSearch(e.target.value);
        setSourceSelected(false);
        setShowSourceResults(true);
    }}
    onFocus={() => setShowSourceResults(true)}
/>

    {showSourceResults && (
        <div className="location-results">
            {filteredSourceLocations.length > 0 ? (
                filteredSourceLocations.map((location) => (
                    <button
                        type="button"
                        key={location}
                        className="location-option"
                        onClick={() => {

                            setSource(location);
                            setSourceSearch(location);
                            setSourceSelected(true);
                            setShowSourceResults(false);
                        }}
                    >
                        {location}
                    </button>
                ))
            ) : (
                <div className="no-results">
                    No locations found
                </div>
            )}
        </div>
    )}
</div>
<div className="form-group location-field">
    <label>Destination</label>
<input
    placeholder="Search destination city..."
    value={destinationSearch}
    onChange={(e) => {
        setDestinationSearch(e.target.value);
        setDestinationSelected(false);
        setShowDestinationResults(true);
    }}
    onFocus={() => setShowDestinationResults(true)}
/>

    {showDestinationResults && (
        <div className="location-results">
            {filteredDestinationLocations.length > 0 ? (
                filteredDestinationLocations.map((location) => (
                    <button
                        type="button"
                        key={location}
                        className="location-option"
                        onClick={() => {
                            setDestination(location);
                            setDestinationSearch(location);
                            setDestinationSelected(true);
                            setShowDestinationResults(false);
                        }}
                    >
                        {location}
                    </button>
                ))
            ) : (
                <div className="no-results">
                    No locations found
                </div>
            )}
        </div>
    )}
</div>
            <div className="form-group">
                <label>Days</label>

                <input
                    type="number"
                    min="1"
                    max="30"
                    value={days}
                    onChange={(e) =>
                        setDays(
                            Number(e.target.value)
                        )
                    }
                />
            </div>

            <div className="form-group">
                <label>Budget</label>

                <select
                    value={budget}
                    onChange={(e) =>
                        setBudget(e.target.value)
                    }
                >
                    <option value="Low">
                        Low
                    </option>

                    <option value="Medium">
                        Medium
                    </option>

                    <option value="High">
                        High
                    </option>
                </select>
            </div>

            <div className="form-group">
                <label>Travel Mode</label>

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
                    <option value="car">
                        Car
                    </option>

                    <option value="bus">
                        Bus
                    </option>

                    <option value="train">
                        Train
                    </option>

                    <option value="flight">
                        Flight
                    </option>
                </select>
            </div>

            <button
                type="submit"
                style={{
                    marginTop: 10,
                    padding: 10,
                    background: "#4caf50",
                    color: "white",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                }}
            >
                Plan Trip
            </button>
        </form>
    );
}