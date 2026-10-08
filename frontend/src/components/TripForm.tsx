import { useState } from "react";
import type { DestinationStop, TravelerRequest, TripRequest } from "../types/trip";
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
    const [isMultiDest, setIsMultiDest] = useState(false);
    const [multiStops, setMultiStops] = useState<DestinationStop[]>([
        { name: locations.India[0], days: 2 },
        { name: locations.India[8], days: 1 },
        { name: locations.India[7], days: 2 },
    ]);
    const [source, setSource] = useState<string>(
    previousTrip?.source ?? locations.India[1]
);
    const [sourceSelected, setSourceSelected] = useState(true);
const [destinationSelected, setDestinationSelected] = useState(true);
const [destination, setDestination] = useState<string>(
    previousTrip?.destination ?? locations.India[0]
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

    // Planning Constraints State
    const [showConstraints, setShowConstraints] = useState(false);
    const [maxDailyDistance, setMaxDailyDistance] = useState<string>("");
    const [maxBudgetCap, setMaxBudgetCap] = useState<string>("");
    const [minAttractionsPerDay, setMinAttractionsPerDay] = useState<string>("");
    const [mustVisitInput, setMustVisitInput] = useState<string>("");
    const [avoidLocationsInput, setAvoidLocationsInput] = useState<string>("");

    const getParsedConstraints = () => {
        const c: any = {};
        if (maxDailyDistance.trim()) {
            const v = parseFloat(maxDailyDistance);
            if (!isNaN(v) && v > 0) c.max_daily_distance_km = v;
        }
        if (maxBudgetCap.trim()) {
            const v = parseFloat(maxBudgetCap);
            if (!isNaN(v) && v > 0) c.max_budget = v;
        }
        if (minAttractionsPerDay.trim()) {
            const v = parseInt(minAttractionsPerDay);
            if (!isNaN(v) && v > 0) c.min_attractions_per_day = v;
        }
        if (mustVisitInput.trim()) {
            const arr = mustVisitInput.split(",").map((s) => s.trim()).filter(Boolean);
            if (arr.length > 0) c.must_visit_locations = arr;
        }
        if (avoidLocationsInput.trim()) {
            const arr = avoidLocationsInput.split(",").map((s) => s.trim()).filter(Boolean);
            if (arr.length > 0) c.locations_to_avoid = arr;
        }
        return Object.keys(c).length > 0 ? c : undefined;
    };

    const handleSubmit = (
    e: React.FormEvent<HTMLFormElement>
) => {
    e.preventDefault();
    const constraintsObj = getParsedConstraints();

    if (isMultiDest) {
        if (multiStops.length < 2) {
            alert("Please add at least 2 destination stops for a multi-destination trip.");
            return;
        }
        for (const s of multiStops) {
            if (!s.name.trim()) {
                alert("Please ensure all destination stops have a selected city.");
                return;
            }
        }
        const totalDays = multiStops.reduce((sum, s) => sum + (Number(s.days) || 1), 0);
        const compositeDest = multiStops.map(s => s.name.split(",")[0].trim()).join(" -> ");
        onSubmit({
            source,
            destination: compositeDest,
            days: totalDays,
            destinations: multiStops,
            travelers,
            mandatory_visits: [],
            constraints: constraintsObj,
            travel_mode: travelMode,
        });
        return;
    }

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
        constraints: constraintsObj,
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
                "Food",
                "History",
                "Culture",
                "Nature",
                "Adventure",
                "Beaches",
                "Shopping",
                "Religion",
                "Nightlife",
                "Photography",
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

    {/* Single vs Multi-Destination Mode Toggle */}
    <div style={{ display: "flex", gap: 10, margin: "20px 0" }}>
        <button
            type="button"
            onClick={() => setIsMultiDest(false)}
            style={{
                flex: 1,
                padding: "10px",
                borderRadius: 8,
                fontWeight: 600,
                fontSize: "0.9rem",
                cursor: "pointer",
                border: !isMultiDest ? "2px solid #4f46e5" : "1px solid #cbd5e1",
                background: !isMultiDest ? "#eef2ff" : "#fff",
                color: !isMultiDest ? "#4f46e5" : "#64748b",
            }}
        >
            📍 Single Destination
        </button>
        <button
            type="button"
            onClick={() => setIsMultiDest(true)}
            style={{
                flex: 1,
                padding: "10px",
                borderRadius: 8,
                fontWeight: 600,
                fontSize: "0.9rem",
                cursor: "pointer",
                border: isMultiDest ? "2px solid #4f46e5" : "1px solid #cbd5e1",
                background: isMultiDest ? "#eef2ff" : "#fff",
                color: isMultiDest ? "#4f46e5" : "#64748b",
            }}
        >
            🗺️ Multi-Destination Tour (Multiple Cities)
        </button>
    </div>

    <div className="form-group location-field">
        <label>Origin / Departure City</label>
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
                    filteredSourceLocations.map((loc) => (
                        <button
                            type="button"
                            key={loc}
                            className="location-option"
                            onClick={() => {
                                setSource(loc);
                                setSourceSearch(loc);
                                setSourceSelected(true);
                                setShowSourceResults(false);
                            }}
                        >
                            {loc}
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

    {isMultiDest ? (
        <div style={{ background: "#f8fafc", padding: 16, borderRadius: 10, border: "1px solid #e2e8f0", marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span style={{ fontWeight: 700, color: "#1e293b", fontSize: "0.95rem" }}>
                    Destinations & Days per City
                </span>
                <span style={{ fontSize: "0.82rem", color: "#64748b" }}>
                    Total: {multiStops.reduce((sum, s) => sum + (Number(s.days) || 1), 0)} Days
                </span>
            </div>

            {multiStops.map((stop, idx) => (
                <div key={idx} style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#4f46e5", minWidth: 60 }}>
                        Stop {idx + 1}:
                    </span>
                    <select
                        value={stop.name}
                        onChange={(e) => {
                            const updated = [...multiStops];
                            updated[idx].name = e.target.value;
                            setMultiStops(updated);
                        }}
                        style={{ flex: 1, minWidth: 200, padding: "8px 12px", borderRadius: 6, border: "1px solid #cbd5e1", background: "#fff" }}
                    >
                        {allLocations.map((loc) => (
                            <option key={loc} value={loc}>{loc}</option>
                        ))}
                    </select>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <input
                            type="number"
                            min="1"
                            max="14"
                            value={stop.days}
                            onChange={(e) => {
                                const updated = [...multiStops];
                                updated[idx].days = Math.max(1, parseInt(e.target.value) || 1);
                                setMultiStops(updated);
                            }}
                            style={{ width: 55, padding: "8px", borderRadius: 6, border: "1px solid #cbd5e1", textAlign: "center" }}
                        />
                        <span style={{ fontSize: "0.82rem", color: "#64748b" }}>days</span>
                    </div>
                    {multiStops.length > 2 && (
                        <button
                            type="button"
                            onClick={() => setMultiStops(multiStops.filter((_, i) => i !== idx))}
                            style={{ background: "#fee2e2", color: "#dc2626", border: "none", borderRadius: 6, padding: "8px 10px", cursor: "pointer", fontWeight: 700 }}
                            title="Remove destination stop"
                        >
                            ✕
                        </button>
                    )}
                </div>
            ))}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                <button
                    type="button"
                    onClick={() => setMultiStops([...multiStops, { name: locations.India[3], days: 2 }])}
                    style={{ background: "#eef2ff", color: "#4f46e5", border: "1px dashed #4f46e5", borderRadius: 6, padding: "7px 14px", fontWeight: 600, fontSize: "0.84rem", cursor: "pointer" }}
                >
                    + Add Another City
                </button>
                <div style={{ fontSize: "0.85rem", color: "#475569" }}>
                    Route: {source.split(",")[0]} ➔ {multiStops.map(s => s.name.split(",")[0]).join(" ➔ ")}
                </div>
            </div>
        </div>
    ) : (
        <>
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
                            filteredDestinationLocations.map((loc) => (
                                <button
                                    type="button"
                                    key={loc}
                                    className="location-option"
                                    onClick={() => {
                                        setDestination(loc);
                                        setDestinationSearch(loc);
                                        setDestinationSelected(true);
                                        setShowDestinationResults(false);
                                    }}
                                >
                                    {loc}
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
                    onChange={(e) => setDays(Number(e.target.value))}
                />
            </div>
        </>
    )}

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

            {/* Planning Constraints Collapsible Section */}
            <div style={{ margin: "20px 0", border: "1px solid #e2e8f0", borderRadius: 8, padding: 14, background: "#f8fafc" }}>
                <div
                    onClick={() => setShowConstraints(!showConstraints)}
                    style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", fontWeight: 600, color: "#1e293b" }}
                >
                    <span style={{ fontSize: "0.92rem" }}>⚙️ Custom Planning Constraints (Optional)</span>
                    <span style={{ fontSize: "0.82rem", color: "#4f46e5" }}>{showConstraints ? "▲ Hide" : "▼ Show"}</span>
                </div>

                {showConstraints && (
                    <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>
                                Max Daily Travel Distance (km)
                            </label>
                            <input
                                type="number"
                                placeholder="e.g. 25"
                                value={maxDailyDistance}
                                onChange={(e) => setMaxDailyDistance(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>
                                Max Budget Cap (₹ INR)
                            </label>
                            <input
                                type="number"
                                placeholder="e.g. 50000"
                                value={maxBudgetCap}
                                onChange={(e) => setMaxBudgetCap(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>
                                Min Attractions Per Day
                            </label>
                            <input
                                type="number"
                                placeholder="e.g. 2"
                                min="1"
                                max="6"
                                value={minAttractionsPerDay}
                                onChange={(e) => setMinAttractionsPerDay(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>
                                Must-Visit Attractions
                            </label>
                            <input
                                type="text"
                                placeholder="Comma separated, e.g. Fort, Church"
                                value={mustVisitInput}
                                onChange={(e) => setMustVisitInput(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                            />
                        </div>
                        <div style={{ gridColumn: "1 / -1" }}>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>
                                Locations / Keywords to Avoid
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. Crowded Pubs, Extreme Adventure"
                                value={avoidLocationsInput}
                                onChange={(e) => setAvoidLocationsInput(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                            />
                        </div>
                    </div>
                )}
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