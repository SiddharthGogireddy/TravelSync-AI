
import Dashboard from "../components/Dashboard";

import type { TripApiResponse, Place } from "../types/api";


interface Props {
    data: TripApiResponse;
}

export default function Results({ data }: Props) {
    

    const dashboard = data.dashboard;
    const trip = data.trip;
    const itinerary = data.itinerary;

    // ✅ SAFE fallback (trip_id may not exist)
    const shareUrl = `${window.location.origin}/trip/demo`;

    // ✅ SAFE schedule typing
    const schedule: Record<string, Place[]> =
        trip?.day_schedule ?? {};

    return (
        <div style={{ padding: 20 }}>

            {/* Dashboard */}
            {dashboard && <Dashboard dashboard={dashboard} />}

            {/* Share */}
            <div>
                <h3>Share</h3>
                <input value={shareUrl} readOnly />
            </div>

            {/* Travelers */}
            <h2>Travelers</h2>
            {trip?.travelers?.map((t, i) => (
                <div key={i}>
                    {t?.name ?? "Unknown"} — ₹{t?.budget ?? 0}
                </div>
            ))}

            {/* Weather */}
            <h2>Weather</h2>
            {trip?.weather?.map((w, i) => (
                <div key={i}>
                    {w?.date ?? "N/A"} — {w?.max_temp ?? 0}° / {w?.min_temp ?? 0}°
                </div>
            ))}

            {/* Hotels */}
            <h2>Hotels</h2>
            {trip?.hotels?.map((h, i) => (
                <div key={i}>
                    {h?.name ?? "Hotel"} — {h?.distance ?? 0} km
                </div>
            ))}

            {/* Daily Plan */}
            <h2>Daily Plan</h2>
            {Object.entries(schedule).map(([day, places]) => (
                <div key={day}>
                    <h3>{day}</h3>

                    {(places ?? []).map((p, i) => (
                        <div key={i}>
                            {p?.name ?? "Place"} (
                            {p?.type ?? p?.category ?? "General"})
                        </div>
                    ))}
                </div>
            ))}

            {/* Itinerary */}
            <h2>AI Itinerary</h2>
            <div style={{ whiteSpace: "pre-wrap" }}>
                {itinerary?.itinerary ?? ""}
            </div>
        </div>
    );
}