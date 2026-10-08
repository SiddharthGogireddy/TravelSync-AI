import type { Place } from "../types/api";

import "../styles/DayCard.css";
interface Props {
    day: string;
    places: Place[];
    TravelMode: string;
    onSelect: (place: Place) => void;
    onRegenerate?: (day: string) => void;
}

const TIMES = [
    "09:00 AM",
    "11:00 AM",
    "02:00 PM",
    "05:00 PM"
];

function estimateTravelTime(distance: number, mode: string) {
    const speeds: Record<string, number> = {
        car: 35,
        bus: 25,
        train: 40,
        flight: 500,
    };

    const speed = speeds[mode?.toLowerCase()] ?? 35;

    const hours = distance / speed;

    if (hours < 1) {
        return `${Math.round(hours * 60)} min`;
    }

    return `${hours.toFixed(1)} hrs`;
}
export default function DayCard({
    day,
    places,
    onSelect,
    onRegenerate,
    TravelMode,
}: Props) {
    const totalTravelDistance = places.reduce(
    (total, place) =>
        total + (place.travel_from_previous_km ?? 0),
    0
);
    const totalTravelTime = places.reduce(
    (total, place) => {
        if (place.travel_from_previous_km == null) {
            return total;
        }

        const speeds: Record<string, number> = {
            car: 35,
            bus: 25,
            train: 40,
            flight: 500,
        };

        const speed =
            speeds[TravelMode?.toLowerCase()] ?? 30;

        return total + place.travel_from_previous_km / speed;
    },
    0
);
    return (
        <div className="day-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                <h3 style={{ margin: 0 }}>Day {day}</h3>
                <div style={{ display: "flex", gap: 12, fontSize: "0.82rem", color: "#64748b", fontWeight: 500 }}>
                    <span>📍 <strong>{places.length}</strong> Stops</span>
                    <span>🚗 <strong>{totalTravelDistance.toFixed(1)} km</strong></span>
                    <span>⏱️ <strong>~{Math.round(totalTravelTime * 60)} min</strong> transit</span>
                </div>
            </div>

            {places.map((place, index) => {
                const displayTime = place.time_window || (place.arrival_time && place.departure_time ? `${place.arrival_time} - ${place.departure_time}` : TIMES[index] || "06:00 PM");
                const travelDurationStr = place.travel_time_minutes ? `${place.travel_time_minutes} min` : estimateTravelTime(place.travel_from_previous_km || 0, TravelMode);


                return (
                    <div
                        key={index}
                        className="attraction-card"
                        onClick={() => onSelect(place)}
                    >
                        <div className="timeline-time" style={{ minWidth: 130 }}>
                            <div style={{ fontWeight: 700, fontSize: "0.85rem", color: "#312e81" }}>
                                {displayTime}
                            </div>
                            {place.opening_hours && (
                                <div style={{ fontSize: "0.72rem", color: place.is_open_on_arrival === false ? "#b91c1c" : "#16a34a", marginTop: 2, display: "flex", alignItems: "center", gap: 3 }}>
                                    <span>{place.is_open_on_arrival === false ? "⚠️" : "🕒"}</span>
                                    <span>{place.opening_hours.display}</span>
                                </div>
                            )}
                        </div>

                        <div className="attraction-content">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                                <h4 style={{ margin: 0 }}>{place.name}</h4>
                                {place.timing_status && (
                                    <span
                                        style={{
                                            fontSize: "0.72rem",
                                            fontWeight: 600,
                                            padding: "2px 8px",
                                            borderRadius: 10,
                                            background: place.timing_status.includes("Replanned") ? "#fef3c7" : (place.is_open_on_arrival === false ? "#fee2e2" : "#ecfdf5"),
                                            color: place.timing_status.includes("Replanned") ? "#92400e" : (place.is_open_on_arrival === false ? "#991b1b" : "#065f46"),
                                        }}
                                    >
                                        {place.timing_status}
                                    </span>
                                )}
                            </div>

                            <p style={{ margin: "4px 0", color: "#64748b", fontSize: "0.84rem" }}>
                                {place.category} • {place.distance_km} km from center
                            </p>

                            {place.travel_from_previous_km != null && place.travel_from_previous_km > 0 && (
                                <p style={{ margin: "4px 0", fontSize: "0.8rem", color: "#475569", display: "flex", alignItems: "center", gap: 4 }}>
                                    <span>🚗</span>
                                    <span>
                                        <strong>{place.travel_from_previous_km.toFixed(1)} km</strong> ({travelDurationStr}) from previous stop
                                    </span>
                                </p>
                            )}

                            {place.matched_travelers && place.matched_travelers.length > 0 && (
                                <div style={{ marginTop: 6, fontSize: "0.82rem" }}>
                                    <span style={{ color: "#4f46e5", fontWeight: 600 }}>
                                        🎯 Matched:
                                    </span>{" "}
                                    <span style={{ color: "#1e293b", fontWeight: 500 }}>
                                        {place.matched_travelers.join(", ")}
                                    </span>
                                    {place.matched_interests && place.matched_interests.length > 0 && (
                                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                                            {place.matched_interests.map((interest, idx) => (
                                                <span
                                                    key={idx}
                                                    style={{
                                                        background: "#ede9fe",
                                                        color: "#6d28d9",
                                                        fontSize: "0.72rem",
                                                        padding: "2px 7px",
                                                        borderRadius: 10,
                                                        fontWeight: 500,
                                                    }}
                                                >
                                                    #{interest}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                );
            })}

            {onRegenerate && (
    <button
        className="regenerate-button"
        onClick={() => onRegenerate(day)}
    >
        Regenerate Day
    </button>
)}
        </div>
    );
}