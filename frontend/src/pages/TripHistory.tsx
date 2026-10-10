import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getTripHistory } from "../services/api";
import type { TripHistoryItem } from "../services/api";

export function getDestinationTitle(item?: TripHistoryItem | null): string {
  if (!item || typeof item !== "object") {
    return "Unknown destination";
  }

  // Support normalized { data: { trip: ... } } as well as direct trip dictionary
  const trip = item.data?.trip ?? (item.data as Record<string, unknown> | undefined) ?? {};
  const destLoc = trip?.destination_location as { lat?: unknown; lon?: unknown } | null | undefined;

  const hasValidCoords =
    destLoc &&
    typeof destLoc.lat === "number" &&
    !isNaN(destLoc.lat) &&
    typeof destLoc.lon === "number" &&
    !isNaN(destLoc.lon);

  if (hasValidCoords) {
    return `Trip at ${(destLoc.lat as number).toFixed(4)}, ${(destLoc.lon as number).toFixed(4)}`;
  }

  const destination = trip?.destination;
  if (typeof destination === "string" && destination.trim()) {
    return `Trip to ${destination.trim()}`;
  }

  return "Unknown destination";
}

export default function TripHistory() {
  const [trips, setTrips] = useState<TripHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    async function loadHistory() {
      try {
        const result = await getTripHistory();
        setTrips(Array.isArray(result) ? result : []);
      } catch (err) {
        console.error(err);
        setError("Failed to load trip history");
      } finally {
        setLoading(false);
      }
    }

    loadHistory();
  }, []);

  if (loading) {
    return (
      <div className="page">
        Loading trip history...
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        {error}
      </div>
    );
  }

  return (
    <div className="page">
      <h2>Trip History</h2>

      {trips.length === 0 ? (
        <p>No saved trips yet.</p>
      ) : (
        trips.map((item, index) => {
          const tripId = item?.id ? String(item.id) : "";
          const trip = item?.data?.trip ?? (item?.data as Record<string, unknown> | undefined) ?? {};
          const destLoc = trip?.destination_location as { lat?: unknown; lon?: unknown } | null | undefined;
          const hasValidCoords =
            destLoc &&
            typeof destLoc.lat === "number" &&
            !isNaN(destLoc.lat) &&
            typeof destLoc.lon === "number" &&
            !isNaN(destLoc.lon);
          const destinationName =
            typeof trip?.destination === "string" && trip.destination.trim()
              ? trip.destination.trim()
              : null;

          return (
            <div
              key={tripId || `trip-${index}`}
              className="card"
              style={{ marginBottom: "15px" }}
            >
              <h3>{getDestinationTitle(item)}</h3>

              {hasValidCoords && destinationName && (
                <p style={{ margin: "4px 0", color: "#4b5563" }}>
                  Destination: {destinationName}
                </p>
              )}

              <p>
                Trip ID: {tripId || "N/A"}
              </p>

              <button
                onClick={() => {
                  if (tripId) {
                    navigate(`/trip/${tripId}`);
                  }
                }}
                disabled={!tripId}
              >
                Open Trip
              </button>
            </div>
          );
        })
      )}
    </div>
  );
}