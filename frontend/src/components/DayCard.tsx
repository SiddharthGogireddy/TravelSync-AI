import type { Place } from "../types/api";

import "../styles/DayCard.css";
interface Props {
    day: string;
    places: Place[];
    onSelect: (place: Place) => void;
    onRegenerate?: (day: string) => void;
}

const TIMES = [
    "09:00 AM",
    "11:00 AM",
    "02:00 PM",
    "05:00 PM"
];

export default function DayCard({
    day,
    places,
    onSelect,
    onRegenerate
}: Props) {
    return (
        <div className="day-card">
            <h3>Day {day}</h3>

            {places.map((place, index) => (
                <div
                    key={index}
                    className="attraction-card"
                    onClick={() => onSelect(place)}
                >
                    <div className="timeline-time">
                        {TIMES[index] || "06:00 PM"}
                    </div>

                    <div className="attraction-content">
                        <h4>{place.name}</h4>

                        <p>
                            {place.category}
                            {" • "}
                            {place.distance_km} km
                        </p>
                    </div>
                </div>
            ))}
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