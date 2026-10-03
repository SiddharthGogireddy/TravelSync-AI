import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getTripHistory } from "../services/api";
import type { TripHistoryItem } from "../services/api";

export default function TripHistory() {
  const [trips, setTrips] = useState<TripHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    async function loadHistory() {
      try {
        const result = await getTripHistory();
        setTrips(result);
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
        trips.map((item) => (
          <div
            key={item.id}
            className="card"
            style={{ marginBottom: "15px" }}
          >
            <h3>
              Trip at{" "}
              {item.data.trip.destination_location.lat.toFixed(4)}
              {", "}
              {item.data.trip.destination_location.lon.toFixed(4)}
            </h3>

            <p>
              Trip ID: {item.id}
            </p>

            <button
              onClick={() =>
                navigate(`/trip/${item.id}`)
              }
            >
              Open Trip
            </button>
          </div>
        ))
      )}
    </div>
  );
}