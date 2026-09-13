import { useState } from "react";
import type { TravelerRequest, TripRequest } from "../types/trip";
import {useLocation} from  "react-router-dom";
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
    const location = useLocation();
    const previousTrip = location.state?.trip;
    const [source, setSource] = useState<string>(
    previousTrip?.source ?? locations.India[0]
);
    const [sourceSelected, setSourceSelected] = useState(true);
const [destinationSelected, setDestinationSelected] = useState(true);
const [destination, setDestination] = useState<string>(
    previousTrip?.destination ?? locations.India[1]
);
    const [days, setDays] = useState(
    previousTrip?.days ?? 3
);
    
    const [travelers, setTravelers] = useState<
    TravelerRequest[]
>(
    previousTrip?.travelers ?? [
        {
            name: "",
            interests: ["Beaches"],
            budget: "Medium",
            pace: "Balanced",
        },
    ]
);
    const [travelMode, setTravelMode] = useState<
        "car" | "bus" | "train" | "flight"
    >(previousTrip?.travel_mode ?? "car");

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
        travelers,

        mandatory_visits: [],
        travel_mode: travelMode,
    });
};
    const [sourceSearch, setSourceSearch] = useState(
    previousTrip?.source ?? ""
);

const [destinationSearch, setDestinationSearch] = useState(
    previousTrip?.destination ?? ""
);

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
    <h3>Travelers</h3>

    {travelers.map((traveler, index) => (
        <div
            key={index}
            className="card"
            style={{ marginBottom: "15px" }}
        >
            <h4>Traveler {index + 1}</h4>

            <label>Name</label>
            <input
                placeholder="Enter name"
                value={traveler.name}
                onChange={(e) => {
                    const updated = [...travelers];

                    updated[index] = {
                        ...updated[index],
                        name: e.target.value,
                    };

                    setTravelers(updated);
                }}
            />

            <label>Budget</label>
            <select
                value={traveler.budget}
                onChange={(e) => {
                    const updated = [...travelers];

                    updated[index] = {
                        ...updated[index],
                        budget: e.target.value,
                    };

                    setTravelers(updated);
                }}
            >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
            </select>

            <label>Interests</label>

            {[
                "Beaches",
                "History",
                "Nature",
                "Food",
                "Shopping",
                "Adventure",
                "Culture",
            ].map((interest) => (
                <label
                    key={interest}
                    style={{
                        display: "block",
                        marginTop: "6px",
                    }}
                >
                    <input
                        type="checkbox"
                        checked={traveler.interests.includes(
                            interest
                        )}
                        onChange={() => {
                            const updated = [...travelers];

                            const currentInterests =
                                traveler.interests;

                            updated[index] = {
                                ...updated[index],
                                interests:
                                    currentInterests.includes(
                                        interest
                                    )
                                        ? currentInterests.filter(
                                              (item) =>
                                                  item !== interest
                                          )
                                        : [
                                              ...currentInterests,
                                              interest,
                                          ],
                            };

                            setTravelers(updated);
                        }}
                    />

                    {" "}
                    {interest}
                </label>
            ))}

            <label>Travel Pace</label>

            <select
                value={traveler.pace}
                onChange={(e) => {
                    const updated = [...travelers];

                    updated[index] = {
                        ...updated[index],
                        pace: e.target.value,
                    };

                    setTravelers(updated);
                }}
            >
                <option value="Relaxed">
                    Relaxed
                </option>
                <option value="Balanced">
                    Balanced
                </option>
                <option value="Fast">
                    Fast
                </option>
            </select>

            {travelers.length > 1 && (
                <button
                    type="button"
                    onClick={() => {
                        setTravelers(
                            travelers.filter(
                                (_, i) => i !== index
                            )
                        );
                    }}
                    style={{
                        marginTop: "10px",
                    }}
                >
                    Remove Traveler
                </button>
            )}
        </div>
    ))}

    <button
        type="button"
        onClick={() => {
            setTravelers([
                ...travelers,
                {
                    name: "",
                    interests: ["Beaches"],
                    budget: "Medium",
                    pace: "Balanced",
                },
            ]);
        }}
    >
        + Add Traveler
    </button>
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