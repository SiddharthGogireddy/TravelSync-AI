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

    const speed = speeds[mode.toLowerCase()] ?? 35;

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
            speeds[TravelMode.toLowerCase()] ?? 30;

        return total + place.travel_from_previous_km / speed;
    },
    0
);
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
                    <div className="day-travel-summary">
    <strong>{places.length} Activities</strong>

    <span>
        {totalTravelDistance.toFixed(1)} km travel
    </span>

    <span>
        ~{Math.round(totalTravelTime * 60)} min travel time
    </span>
</div>
                    <div className="attraction-content">
                        <h4>{place.name}</h4>

                        <p>
                            {place.category}
                            {" • "}
                
                                {place.distance_km} km
                        </p>
   {place.travel_from_previous_km != null && (
    <p>
         {place.travel_from_previous_km.toFixed(1)} km
        {" • "}
        ~{estimateTravelTime(
            place.travel_from_previous_km,
            TravelMode
        )}
        from previous stop
    </p>
)}
                        {place.matched_travelers &&
        place.matched_travelers.length > 0 && (
            <p>
                <strong>Matches:</strong>{" "}
                {place.matched_travelers.join(", ")}
            </p>
        )}
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