import { useState } from "react";
import type { DestinationStop, TravelerRequest, TripRequest, LocationSuggestion } from "../types/trip";
import { useLocation } from "react-router-dom";
import TravelDatePicker from "./TravelDatePicker";
import { FlexibleDateSuggester } from "./FlexibleDateSuggester";
import { calculateDaysBetween } from "../utils/dateUtils";
import { LocationAutocomplete } from "./LocationAutocomplete";
import { Calendar, Sparkles, Check, Trash2, ChevronDown, ChevronUp } from "lucide-react";

const DEFAULT_ORIGIN = "Hyderabad, Telangana, India";
const DEFAULT_DESTINATION = "Bengaluru, Karnataka, India";
const DEFAULT_MULTI_STOPS: DestinationStop[] = [
    { name: "Bengaluru, Karnataka, India", days: 2 },
    { name: "Mysuru, Karnataka, India", days: 1 },
    { name: "Goa, India", days: 2 },
];

export default function TripForm({
    onSubmit,
}: {
    onSubmit: (data: TripRequest) => void;
}) {
    const location = useLocation();
    const previousTrip = location.state?.trip;
    const [isMultiDest, setIsMultiDest] = useState(false);
    const [multiStops, setMultiStops] = useState<DestinationStop[]>(
        previousTrip?.destinations?.length
            ? previousTrip.destinations
            : DEFAULT_MULTI_STOPS
    );
    const [source, setSource] = useState<string>(
        previousTrip?.source ?? DEFAULT_ORIGIN
    );
    const [sourceLocation, setSourceLocation] = useState<LocationSuggestion | null>(null);
    const [sourceSelected, setSourceSelected] = useState(true);

    const [destination, setDestination] = useState<string>(
        previousTrip?.destination ?? DEFAULT_DESTINATION
    );
    const [destinationLocation, setDestinationLocation] = useState<LocationSuggestion | null>(null);
    const [destinationSelected, setDestinationSelected] = useState(true);

    const isSameLocation = (loc1: string, loc2: string) => {
        if (!loc1 || !loc2) return false;
        return loc1.trim().toLowerCase() === loc2.trim().toLowerCase();
    };

    const handleSwapLocations = () => {
        const prevSource = source;
        const prevSourceLoc = sourceLocation;
        const prevSourceSelected = sourceSelected;

        setSource(destination);
        setSourceLocation(destinationLocation);
        setSourceSelected(destinationSelected);

        setDestination(prevSource);
        setDestinationLocation(prevSourceLoc);
        setDestinationSelected(prevSourceSelected);
    };

    const [days, setDays] = useState(
        previousTrip?.days ?? 3
    );
    const [startDate, setStartDate] = useState<string>(
        previousTrip?.start_date ?? ""
    );
    const [endDate, setEndDate] = useState<string>(
        previousTrip?.end_date ?? ""
    );
    const [dateValidationError, setDateValidationError] = useState<string>("");
    const [dateSelectionMode, setDateSelectionMode] = useState<"exact" | "flexible">("exact");

    const handleDatesChange = (newStart: string, newEnd: string, durationDays: number) => {
        setStartDate(newStart);
        setEndDate(newEnd);
        setDateValidationError("");
        if (durationDays > 0) {
            setDays(durationDays);
        }
    };
    
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

    // Validate travel dates
    if (!startDate || !endDate) {
        setDateValidationError("Please select both a start date and an end date on the calendar.");
        alert("Please select both a start date and an end date on the calendar.");
        return;
    }

    if (startDate > endDate) {
        setDateValidationError("End date cannot precede start date.");
        alert("End date cannot precede start date.");
        return;
    }

    const calculatedDays = calculateDaysBetween(startDate, endDate);
    if (calculatedDays < 1 || calculatedDays > 30) {
        setDateValidationError("Trip duration must be between 1 and 30 days.");
        alert("Trip duration must be between 1 and 30 days.");
        return;
    }

    if (isMultiDest) {
        if (!source.trim()) {
            alert("Please specify a departure origin city.");
            return;
        }
        if (!sourceSelected) {
            alert("Please select a verified departure origin city from the suggestions.");
            return;
        }
        if (multiStops.length < 2) {
            alert("Please add at least 2 destination stops for a multi-destination trip.");
            return;
        }
        for (let i = 0; i < multiStops.length; i++) {
            const s = multiStops[i];
            if (!s.name.trim()) {
                alert(`Please ensure Stop ${i + 1} has a selected city.`);
                return;
            }
            if (isSameLocation(source, s.name)) {
                alert(`Stop ${i + 1} (${s.name}) cannot be the same as your departure origin.`);
                return;
            }
            if (i > 0 && isSameLocation(s.name, multiStops[i - 1].name)) {
                alert(`Stop ${i + 1} cannot be identical to the consecutive preceding stop (${s.name}).`);
                return;
            }
        }
        const totalDays = multiStops.reduce((sum, s) => sum + (Number(s.days) || 1), 0);
        if (totalDays !== calculatedDays) {
            alert(`The total duration across your destination stops (${totalDays} days) does not match your selected travel dates (${calculatedDays} days). Please align the duration.`);
            return;
        }
        const compositeDest = multiStops.map(s => s.name.split(",")[0].trim()).join(" -> ");
        onSubmit({
            source,
            destination: compositeDest,
            days: calculatedDays,
            start_date: startDate,
            end_date: endDate,
            destinations: multiStops,
            travelers,
            mandatory_visits: [],
            constraints: constraintsObj,
            travel_mode: travelMode,
        });
        return;
    }

    if (!source.trim() || !destination.trim()) {
        alert("Please provide both an origin and destination.");
        return;
    }

    if (isSameLocation(source, destination)) {
        alert("Origin and destination cannot be the same location. Please choose distinct places.");
        return;
    }

    if (!sourceSelected || !destinationSelected) {
        alert(
            "Please select a verified source and destination from the suggestions."
        );
        return;
    }

    onSubmit({
        source,
        destination,
        days: calculatedDays,
        start_date: startDate,
        end_date: endDate,
        travelers,
        constraints: constraintsObj,
        mandatory_visits: [],
        travel_mode: travelMode,
    });
};

    
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
            Single Destination
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
            Multi-Destination Tour (Multiple Cities)
        </button>
    </div>

    {/* Origin / Departure City */}
    <div className="form-group location-field" style={{ marginBottom: "16px" }}>
        <LocationAutocomplete
            id="trip-origin"
            label="Origin / Departure City"
            placeholder="Search departure city (e.g. London, New York, Mumbai)..."
            value={source}
            isValid={sourceSelected}
            required
            onChange={(val, suggestion) => {
                setSource(val);
                setSourceLocation(suggestion || null);
                setSourceSelected(Boolean(suggestion));
            }}
            error={
                !isMultiDest && source && destination && isSameLocation(source, destination)
                    ? "Origin and destination cannot be the same place."
                    : undefined
            }
        />
    </div>

    {/* Swap Origin & Destination Button for Single Destination Mode */}
    {!isMultiDest && (
        <div style={{ display: "flex", justifyContent: "center", margin: "-6px 0 10px 0" }}>
            <button
                type="button"
                onClick={handleSwapLocations}
                aria-label="Swap origin and destination"
                title="Swap origin and destination"
                style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "6px 14px",
                    borderRadius: "20px",
                    border: "1px solid #cbd5e1",
                    background: "#f8fafc",
                    color: "#4f46e5",
                    fontWeight: 600,
                    fontSize: "0.82rem",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#eef2ff";
                    e.currentTarget.style.borderColor = "#818cf8";
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.background = "#f8fafc";
                    e.currentTarget.style.borderColor = "#cbd5e1";
                }}
            >
                <span style={{ fontSize: "1rem" }}>⇄</span>
                <span>Swap Origin &amp; Destination</span>
            </button>
        </div>
    )}

    {isMultiDest ? (
        <div style={{ background: "#f8fafc", padding: 16, borderRadius: 10, border: "1px solid #e2e8f0", marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span style={{ fontWeight: 700, color: "#1e293b", fontSize: "0.95rem" }}>
                    Destinations &amp; Days per City
                </span>
                <span style={{ fontSize: "0.82rem", color: "#64748b" }}>
                    Total: {multiStops.reduce((sum, s) => sum + (Number(s.days) || 1), 0)} Days
                </span>
            </div>

            {multiStops.map((stop, idx) => (
                <div
                    key={idx}
                    style={{
                        display: "flex",
                        gap: 10,
                        alignItems: "flex-start",
                        marginBottom: 12,
                        flexWrap: "wrap",
                        background: "#ffffff",
                        padding: "10px",
                        borderRadius: "8px",
                        border: "1px solid #e2e8f0",
                    }}
                >
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#4f46e5", minWidth: 60, marginTop: "8px" }}>
                        Stop {idx + 1}:
                    </span>
                    <div style={{ flex: 1, minWidth: 220 }}>
                        <LocationAutocomplete
                            id={`multi-stop-${idx}`}
                            placeholder="Search destination city or landmark..."
                            value={stop.name}
                            isValid={Boolean(stop.name && stop.name.trim())}
                            onChange={(val, suggestion) => {
                                const updated = [...multiStops];
                                updated[idx] = {
                                    ...updated[idx],
                                    name: val,
                                    location: suggestion
                                        ? { lat: suggestion.latitude, lon: suggestion.longitude }
                                        : updated[idx].location,
                                };
                                setMultiStops(updated);
                            }}
                            error={
                                isSameLocation(source, stop.name)
                                    ? "Stop cannot be same as departure origin"
                                    : idx > 0 && isSameLocation(stop.name, multiStops[idx - 1].name)
                                    ? "Stop cannot match previous consecutive stop"
                                    : undefined
                            }
                        />
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: "4px" }}>
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
                            title="Days at this destination stop"
                        />
                        <span style={{ fontSize: "0.82rem", color: "#64748b" }}>days</span>
                    </div>
                    {multiStops.length > 2 && (
                        <button
                            type="button"
                            onClick={() => setMultiStops(multiStops.filter((_, i) => i !== idx))}
                            style={{
                                background: "rgba(239, 68, 68, 0.1)",
                                color: "#ef4444",
                                border: "1px solid rgba(239, 68, 68, 0.25)",
                                borderRadius: 6,
                                padding: "8px 10px",
                                cursor: "pointer",
                                fontWeight: 700,
                                marginTop: "4px",
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center",
                            }}
                            title="Remove destination stop"
                        >
                            <Trash2 size={14} />
                        </button>
                    )}
                </div>
            ))}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                <button
                    type="button"
                    onClick={() => setMultiStops([...multiStops, { name: "", days: 2 }])}
                    style={{
                        background: "var(--accent-bg)",
                        color: "var(--accent)",
                        border: "1px dashed var(--accent-border)",
                        borderRadius: 6,
                        padding: "7px 14px",
                        fontWeight: 600,
                        fontSize: "0.84rem",
                        cursor: "pointer",
                    }}
                >
                    + Add Another City
                </button>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    Route: {source.split(",")[0] || "Origin"} &rarr; {multiStops.map(s => s.name.split(",")[0] || "Stop").join(" &rarr; ")}
                </div>
            </div>
        </div>
    ) : (
        <>
            <div className="form-group location-field" style={{ marginBottom: "16px" }}>
                <LocationAutocomplete
                    id="trip-destination"
                    label="Destination"
                    placeholder="Search destination city, region, or landmark..."
                    value={destination}
                    isValid={destinationSelected}
                    required
                    onChange={(val, suggestion) => {
                        setDestination(val);
                        setDestinationLocation(suggestion || null);
                        setDestinationSelected(Boolean(suggestion));
                    }}
                    error={
                        source && destination && isSameLocation(source, destination)
                            ? "Origin and destination cannot be the same place."
                            : undefined
                    }
                />
            </div>

            <div className="form-group">
                <label>Trip Duration (Days)</label>
                <input
                    type="number"
                    min="1"
                    max="30"
                    value={days}
                    readOnly={Boolean(startDate && endDate)}
                    onChange={(e) => setDays(Number(e.target.value))}
                    style={startDate && endDate ? { background: "var(--code-bg)", color: "var(--text-muted)" } : {}}
                    title={startDate && endDate ? "Auto-calculated from selected travel dates" : ""}
                />
                {startDate && endDate && (
                    <small style={{ color: "var(--accent)", display: "block", marginTop: "4px", fontWeight: 600 }}>
                        Auto-calculated from selected travel dates ({days} {days === 1 ? "day" : "days"})
                    </small>
                )}
            </div>
        </>
    )}

    {/* Month-Specific Travel Date Selection */}
    <div className="form-group" style={{ margin: "20px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
            <div>
                <label style={{ display: "block", fontWeight: 700, color: "var(--input-label)", fontSize: "0.95rem" }}>
                    Travel Dates & Scheduling
                </label>
                <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                    Pick exact calendar dates, or let TravelSync AI rank the best travel window using meteorological forecasts.
                </p>
            </div>

            {/* Mode Switcher */}
            <div style={{ display: "inline-flex", background: "var(--toggle-bg)", padding: "3px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                <button
                    type="button"
                    onClick={() => setDateSelectionMode("exact")}
                    style={{
                        padding: "5px 12px",
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        borderRadius: "6px",
                        border: "none",
                        cursor: "pointer",
                        background: dateSelectionMode === "exact" ? "var(--card-bg)" : "transparent",
                        color: dateSelectionMode === "exact" ? "var(--accent)" : "var(--text-muted)",
                        boxShadow: dateSelectionMode === "exact" ? "var(--shadow)" : "none",
                        transition: "all 0.15s ease",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                    }}
                >
                    <Calendar size={14} />
                    <span>Exact Dates</span>
                </button>
                <button
                    type="button"
                    onClick={() => setDateSelectionMode("flexible")}
                    style={{
                        padding: "5px 12px",
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        borderRadius: "6px",
                        border: "none",
                        cursor: "pointer",
                        background: dateSelectionMode === "flexible" ? "var(--card-bg)" : "transparent",
                        color: dateSelectionMode === "flexible" ? "var(--accent)" : "var(--text-muted)",
                        boxShadow: dateSelectionMode === "flexible" ? "var(--shadow)" : "none",
                        transition: "all 0.15s ease",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                    }}
                >
                    <Sparkles size={14} />
                    <span>Suggest Best Dates (Flexible)</span>
                </button>
            </div>
        </div>

        {startDate && endDate && (
            <div
                style={{
                    background: "rgba(16, 185, 129, 0.1)",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                    borderRadius: "8px",
                    padding: "8px 14px",
                    marginBottom: "12px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "0.85rem",
                    color: "var(--text-h)",
                    flexWrap: "wrap",
                    gap: "6px",
                }}
            >
                <span>
                    Selected Window: <strong>{startDate}</strong> &rarr; <strong>{endDate}</strong> ({days} {days === 1 ? "day" : "days"})
                </span>
                <span style={{ fontSize: "0.78rem", color: "#10b981", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: "4px" }}>
                    <Check size={14} />
                    Ready for Itinerary Generation
                </span>
            </div>
        )}

        {dateSelectionMode === "exact" ? (
            <TravelDatePicker
                startDate={startDate}
                endDate={endDate}
                onChange={handleDatesChange}
                maxTripDurationDays={30}
            />
        ) : (
            <FlexibleDateSuggester
                destination={isMultiDest && multiStops[0]?.name ? multiStops[0].name : destination}
                source={source}
                initialDays={days || 3}
                travelers={travelers}
                onSelectDates={(newStart, newEnd, duration) => {
                    handleDatesChange(newStart, newEnd, duration);
                }}
                currentStartDate={startDate}
                currentEndDate={endDate}
            />
        )}

        {dateValidationError && (
            <div style={{ color: "#dc2626", fontSize: "0.82rem", marginTop: "6px", fontWeight: 600 }}>
                {dateValidationError}
            </div>
        )}
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

            {/* Planning Constraints Collapsible Section */}
            <div style={{ margin: "20px 0", border: "1px solid var(--border)", borderRadius: 8, padding: 14, background: "var(--code-bg)" }}>
                <div
                    onClick={() => setShowConstraints(!showConstraints)}
                    style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", fontWeight: 600, color: "var(--text-h)" }}
                >
                    <span style={{ fontSize: "0.92rem" }}>Custom Planning Constraints (Optional)</span>
                    <span style={{ fontSize: "0.82rem", color: "var(--accent)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                        {showConstraints ? (
                            <>
                                <ChevronUp size={14} />
                                <span>Hide</span>
                            </>
                        ) : (
                            <>
                                <ChevronDown size={14} />
                                <span>Show</span>
                            </>
                        )}
                    </span>
                </div>

                {showConstraints && (
                    <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: 4 }}>
                                Max Daily Travel Distance (km)
                            </label>
                            <input
                                type="number"
                                placeholder="e.g. 25"
                                value={maxDailyDistance}
                                onChange={(e) => setMaxDailyDistance(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: 4 }}>
                                Max Budget Cap (₹ INR)
                            </label>
                            <input
                                type="number"
                                placeholder="e.g. 50000"
                                value={maxBudgetCap}
                                onChange={(e) => setMaxBudgetCap(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: 4 }}>
                                Min Attractions Per Day
                            </label>
                            <input
                                type="number"
                                placeholder="e.g. 2"
                                min="1"
                                max="6"
                                value={minAttractionsPerDay}
                                onChange={(e) => setMinAttractionsPerDay(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", boxSizing: "border-box" }}
                            />
                        </div>
                        <div>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: 4 }}>
                                Must-Visit Attractions
                            </label>
                            <input
                                type="text"
                                placeholder="Comma separated, e.g. Fort, Church"
                                value={mustVisitInput}
                                onChange={(e) => setMustVisitInput(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", boxSizing: "border-box" }}
                            />
                        </div>
                        <div style={{ gridColumn: "1 / -1" }}>
                            <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: 4 }}>
                                Locations / Keywords to Avoid
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. Crowded Pubs, Extreme Adventure"
                                value={avoidLocationsInput}
                                onChange={(e) => setAvoidLocationsInput(e.target.value)}
                                style={{ width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", boxSizing: "border-box" }}
                            />
                        </div>
                    </div>
                )}
            </div>

            <button
                type="submit"
                style={{
                    marginTop: 10,
                    padding: "12px 20px",
                    background: "var(--accent)",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 8,
                    cursor: "pointer",
                    fontWeight: 700,
                    fontSize: "1rem",
                    transition: "background 0.2s ease",
                }}
            >
                Plan Trip
            </button>
        </form>
    );
}