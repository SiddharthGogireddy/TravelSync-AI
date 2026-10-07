import { useEffect, useState } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import {
  getTripHistory,
  compareTrips,
  downloadTripPdf,
  type TripHistoryItem,
  type TripComparisonResult,
} from "../services/api";

export default function TripComparison() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [historyTrips, setHistoryTrips] = useState<TripHistoryItem[]>([]);
  const [trip1Id, setTrip1Id] = useState(searchParams.get("trip1") || "");
  const [trip2Id, setTrip2Id] = useState(searchParams.get("trip2") || "");

  const [loadingHistory, setLoadingHistory] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [comparisonResult, setComparisonResult] =
    useState<TripComparisonResult | null>(null);
  const [error, setError] = useState("");

  // Load history trips for selectors
  useEffect(() => {
    async function loadHistory() {
      try {
        const list = await getTripHistory();
        setHistoryTrips(list);

        // Pre-select defaults if not set and trips are available
        if (!trip1Id && list.length > 0) {
          setTrip1Id(list[0].id);
        }
        if (!trip2Id && list.length > 1) {
          setTrip2Id(list[1].id);
        }
      } catch (err) {
        console.error("Failed to load trips for comparison:", err);
      } finally {
        setLoadingHistory(false);
      }
    }
    loadHistory();
  }, []);

  // Run comparison
  const handleCompare = async (id1: string, id2: string) => {
    if (!id1.trim() || !id2.trim()) {
      setError("Please select or enter both Trip IDs to compare");
      return;
    }

    if (id1.trim() === id2.trim()) {
      setError("Please select two different trips to compare");
      return;
    }

    try {
      setError("");
      setComparing(true);
      const result = await compareTrips(id1.trim(), id2.trim());
      setComparisonResult(result);
      setSearchParams({ trip1: id1.trim(), trip2: id2.trim() });
    } catch (err: any) {
      setError(err.message || "Failed to compare trips");
      setComparisonResult(null);
    } finally {
      setComparing(false);
    }
  };

  // Auto-compare if both trip IDs are present in URL on mount
  useEffect(() => {
    const q1 = searchParams.get("trip1");
    const q2 = searchParams.get("trip2");
    if (q1 && q2 && q1 !== q2) {
      handleCompare(q1, q2);
    }
  }, []);

  const getTripLabel = (item: TripHistoryItem) => {
    const t = item.data?.trip;
    if (!t) return `Trip ${item.id.slice(0, 8)}`;
    const src = t.source ? t.source.split(",")[0] : "Source";
    const dst = t.destination ? t.destination.split(",")[0] : "Destination";
    const days = t.days ? `${t.days}d` : "";
    return `${src} → ${dst} (${days}) • ${item.id.slice(0, 8)}`;
  };

  const comp = comparisonResult?.comparison;
  const t1 = comparisonResult?.trip1;
  const t2 = comparisonResult?.trip2;

  return (
    <div
      style={{
        maxWidth: 1040,
        margin: "30px auto",
        padding: "0 20px",
        textAlign: "left",
      }}
    >
      <div style={{ marginBottom: 16 }}>
        <Link
          to="/"
          style={{
            color: "#4f46e5",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          &larr; Back to Planner
        </Link>
      </div>

      <h1 style={{ textAlign: "left", marginBottom: 6 }}>Trip Comparison</h1>
      <p style={{ color: "#6b7280", marginBottom: 28 }}>
        Compare two saved trips side-by-side to evaluate costs, travel distances, durations, hotels, and itineraries.
      </p>

      {/* Selectors Card */}
      <div
        style={{
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          padding: 24,
          marginBottom: 30,
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr auto",
            gap: 16,
            alignItems: "flex-end",
          }}
        >
          {/* Trip 1 Selector */}
          <div>
            <label
              style={{
                display: "block",
                fontWeight: 600,
                fontSize: "0.9rem",
                color: "#374151",
                marginBottom: 6,
              }}
            >
              Select Trip 1:
            </label>
            <select
              value={trip1Id}
              onChange={(e) => setTrip1Id(e.target.value)}
              disabled={loadingHistory}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #d1d5db",
                background: "#fff",
                fontSize: "0.9rem",
              }}
            >
              <option value="">-- Choose a trip --</option>
              {historyTrips.map((item) => (
                <option key={item.id} value={item.id}>
                  {getTripLabel(item)}
                </option>
              ))}
            </select>
          </div>

          {/* Trip 2 Selector */}
          <div>
            <label
              style={{
                display: "block",
                fontWeight: 600,
                fontSize: "0.9rem",
                color: "#374151",
                marginBottom: 6,
              }}
            >
              Select Trip 2:
            </label>
            <select
              value={trip2Id}
              onChange={(e) => setTrip2Id(e.target.value)}
              disabled={loadingHistory}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #d1d5db",
                background: "#fff",
                fontSize: "0.9rem",
              }}
            >
              <option value="">-- Choose a trip --</option>
              {historyTrips.map((item) => (
                <option key={item.id} value={item.id}>
                  {getTripLabel(item)}
                </option>
              ))}
            </select>
          </div>

          {/* Compare Button */}
          <div>
            <button
              onClick={() => handleCompare(trip1Id, trip2Id)}
              disabled={comparing}
              style={{
                padding: "10px 24px",
                background: "#4f46e5",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                fontWeight: 600,
                cursor: "pointer",
                height: 42,
              }}
            >
              {comparing ? "Comparing..." : "Compare"}
            </button>
          </div>
        </div>

        {error && (
          <p
            style={{
              color: "#dc2626",
              marginTop: 14,
              fontSize: "0.9rem",
              fontWeight: 500,
              background: "#fee2e2",
              padding: "8px 12px",
              borderRadius: 6,
            }}
          >
            {error}
          </p>
        )}
      </div>

      {/* Comparison View */}
      {comparisonResult && t1 && t2 && comp && (
        <div>
          {/* Key Differences Highlight Badges */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 16,
              marginBottom: 30,
            }}
          >
            {/* Cost highlight */}
            <div
              style={{
                background: "#ecfdf5",
                border: "1px solid #a7f3d0",
                padding: 16,
                borderRadius: 10,
              }}
            >
              <div
                style={{
                  fontSize: "0.8rem",
                  color: "#065f46",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Cost Leader
              </div>
              <div
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: "#047857",
                  marginTop: 4,
                }}
              >
                {comp.cheaper_trip_id === "equal"
                  ? "Equal Estimated Cost"
                  : comp.cheaper_trip_id === t1.trip_id
                  ? "Trip 1 is Cheaper"
                  : "Trip 2 is Cheaper"}
              </div>
              <div style={{ fontSize: "0.85rem", color: "#065f46", marginTop: 2 }}>
                {comp.cheaper_trip_id === "equal"
                  ? "Both have the same estimated cost"
                  : `Saves Rs. ${comp.cost_difference.toLocaleString()}`}
              </div>
            </div>

            {/* Duration highlight */}
            <div
              style={{
                background: "#f0f9ff",
                border: "1px solid #bae6fd",
                padding: 16,
                borderRadius: 10,
              }}
            >
              <div
                style={{
                  fontSize: "0.8rem",
                  color: "#0369a1",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Duration
              </div>
              <div
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: "#0284c7",
                  marginTop: 4,
                }}
              >
                {comp.shorter_duration_trip_id === "equal"
                  ? "Same Duration"
                  : comp.shorter_duration_trip_id === t1.trip_id
                  ? "Trip 1 is Shorter"
                  : "Trip 2 is Shorter"}
              </div>
              <div style={{ fontSize: "0.85rem", color: "#0369a1", marginTop: 2 }}>
                {comp.duration_difference_days === 0
                  ? `Both trips are ${t1.duration_days} days`
                  : `Difference of ${comp.duration_difference_days} day(s)`}
              </div>
            </div>

            {/* Distance highlight */}
            <div
              style={{
                background: "#faf5ff",
                border: "1px solid #e9d5ff",
                padding: 16,
                borderRadius: 10,
              }}
            >
              <div
                style={{
                  fontSize: "0.8rem",
                  color: "#6b21a8",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Travel Distance
              </div>
              <div
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: "#7e22ce",
                  marginTop: 4,
                }}
              >
                {comp.shorter_distance_trip_id === "equal"
                  ? "Equal Distance"
                  : comp.shorter_distance_trip_id === t1.trip_id
                  ? "Trip 1 has Less Travel"
                  : "Trip 2 has Less Travel"}
              </div>
              <div style={{ fontSize: "0.85rem", color: "#6b21a8", marginTop: 2 }}>
                {comp.distance_difference_km === 0
                  ? `Both cover ${t1.total_distance_km} km`
                  : `Difference of ${comp.distance_difference_km} km`}
              </div>
            </div>

            {/* Attractions highlight */}
            <div
              style={{
                background: "#fffbeb",
                border: "1px solid #fde68a",
                padding: 16,
                borderRadius: 10,
              }}
            >
              <div
                style={{
                  fontSize: "0.8rem",
                  color: "#92400e",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                Sightseeing
              </div>
              <div
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  color: "#b45309",
                  marginTop: 4,
                }}
              >
                {comp.more_attractions_trip_id === "equal"
                  ? "Equal Attractions"
                  : comp.more_attractions_trip_id === t1.trip_id
                  ? "Trip 1 has More Places"
                  : "Trip 2 has More Places"}
              </div>
              <div style={{ fontSize: "0.85rem", color: "#92400e", marginTop: 2 }}>
                {comp.attractions_difference === 0
                  ? `Both feature ${t1.attractions_count} places`
                  : `${comp.attractions_difference} more attractions scheduled`}
              </div>
            </div>
          </div>

          {/* Detailed Side-by-Side Table */}
          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              overflow: "hidden",
              marginBottom: 30,
              boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "left",
              }}
            >
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "2px solid #e5e7eb" }}>
                  <th style={{ padding: "14px 18px", width: "24%", color: "#374151" }}>
                    Metric
                  </th>
                  <th style={{ padding: "14px 18px", width: "38%", color: "#1f2937" }}>
                    Trip 1: {t1.source.split(",")[0]} → {t1.destination.split(",")[0]}
                  </th>
                  <th style={{ padding: "14px 18px", width: "38%", color: "#1f2937" }}>
                    Trip 2: {t2.source.split(",")[0]} → {t2.destination.split(",")[0]}
                  </th>
                </tr>
              </thead>
              <tbody>
                {/* Source & Destination */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Origin / Destination
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <b>From:</b> {t1.source}<br />
                    <b>To:</b> {t1.destination}
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <b>From:</b> {t2.source}<br />
                    <b>To:</b> {t2.destination}
                  </td>
                </tr>

                {/* Duration */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Duration
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.shorter_duration_trip_id === t1.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    <b>{t1.duration_days} days</b>
                    {comp.shorter_duration_trip_id === t1.trip_id && (
                      <span style={{ color: "#16a34a", fontSize: "0.85rem", marginLeft: 8 }}>
                        (Shorter)
                      </span>
                    )}
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.shorter_duration_trip_id === t2.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    <b>{t2.duration_days} days</b>
                    {comp.shorter_duration_trip_id === t2.trip_id && (
                      <span style={{ color: "#16a34a", fontSize: "0.85rem", marginLeft: 8 }}>
                        (Shorter)
                      </span>
                    )}
                  </td>
                </tr>

                {/* Travel Mode */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Travel Mode
                  </td>
                  <td style={{ padding: "12px 18px", textTransform: "capitalize" }}>
                    {t1.travel_mode}
                  </td>
                  <td style={{ padding: "12px 18px", textTransform: "capitalize" }}>
                    {t2.travel_mode}
                  </td>
                </tr>

                {/* Distance */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Total Distance
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.shorter_distance_trip_id === t1.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    {t1.total_distance_km} km
                    {comp.shorter_distance_trip_id === t1.trip_id && (
                      <span style={{ color: "#16a34a", fontSize: "0.85rem", marginLeft: 8 }}>
                        (Less travel)
                      </span>
                    )}
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.shorter_distance_trip_id === t2.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    {t2.total_distance_km} km
                    {comp.shorter_distance_trip_id === t2.trip_id && (
                      <span style={{ color: "#16a34a", fontSize: "0.85rem", marginLeft: 8 }}>
                        (Less travel)
                      </span>
                    )}
                  </td>
                </tr>

                {/* Travelers */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Traveler Count
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    {t1.traveler_count} traveler(s)
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    {t2.traveler_count} traveler(s)
                  </td>
                </tr>

                {/* Total Budget */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Total Budget
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    Rs. {t1.total_budget.toLocaleString()}
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    Rs. {t2.total_budget.toLocaleString()}
                  </td>
                </tr>

                {/* Estimated Cost */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Estimated Cost
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.cheaper_trip_id === t1.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    <b>Rs. {t1.estimated_cost.toLocaleString()}</b>
                    {comp.cheaper_trip_id === t1.trip_id && (
                      <span
                        style={{
                          background: "#dcfce7",
                          color: "#166534",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          marginLeft: 8,
                        }}
                      >
                        Cheaper
                      </span>
                    )}
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.cheaper_trip_id === t2.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    <b>Rs. {t2.estimated_cost.toLocaleString()}</b>
                    {comp.cheaper_trip_id === t2.trip_id && (
                      <span
                        style={{
                          background: "#dcfce7",
                          color: "#166534",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          marginLeft: 8,
                        }}
                      >
                        Cheaper
                      </span>
                    )}
                  </td>
                </tr>

                {/* Remaining Budget */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Remaining Budget
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      color: t1.remaining_budget < 0 ? "#dc2626" : "#059669",
                      fontWeight: 600,
                    }}
                  >
                    Rs. {t1.remaining_budget.toLocaleString()} ({t1.budget_status})
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      color: t2.remaining_budget < 0 ? "#dc2626" : "#059669",
                      fontWeight: 600,
                    }}
                  >
                    Rs. {t2.remaining_budget.toLocaleString()} ({t2.budget_status})
                  </td>
                </tr>

                {/* Hotels */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Hotels
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <b>{t1.hotel_count} hotels considered</b>
                    {t1.hotels.length > 0 && (
                      <div style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: 4 }}>
                        {t1.hotels.slice(0, 3).join(", ")}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <b>{t2.hotel_count} hotels considered</b>
                    {t2.hotels.length > 0 && (
                      <div style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: 4 }}>
                        {t2.hotels.slice(0, 3).join(", ")}
                      </div>
                    )}
                  </td>
                </tr>

                {/* Number of Attractions */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Attractions Scheduled
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.more_attractions_trip_id === t1.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    <b>{t1.attractions_count} places</b>
                    {comp.more_attractions_trip_id === t1.trip_id && (
                      <span style={{ color: "#16a34a", fontSize: "0.85rem", marginLeft: 8 }}>
                        (More places)
                      </span>
                    )}
                  </td>
                  <td
                    style={{
                      padding: "12px 18px",
                      background:
                        comp.more_attractions_trip_id === t2.trip_id
                          ? "#f0fdf4"
                          : "transparent",
                    }}
                  >
                    <b>{t2.attractions_count} places</b>
                    {comp.more_attractions_trip_id === t2.trip_id && (
                      <span style={{ color: "#16a34a", fontSize: "0.85rem", marginLeft: 8 }}>
                        (More places)
                      </span>
                    )}
                  </td>
                </tr>

                {/* Weather Availability */}
                <tr style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Weather Availability
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <b>{t1.weather_days_available} days forecast</b>
                    {t1.weather_summary.length > 0 && (
                      <div style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: 4 }}>
                        {t1.weather_summary.slice(0, 2).map((w, idx) => (
                          <div key={idx}>
                            {w.date}: {w.min_temp}°C - {w.max_temp}°C
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <b>{t2.weather_days_available} days forecast</b>
                    {t2.weather_summary.length > 0 && (
                      <div style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: 4 }}>
                        {t2.weather_summary.slice(0, 2).map((w, idx) => (
                          <div key={idx}>
                            {w.date}: {w.min_temp}°C - {w.max_temp}°C
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>

                {/* Quick Actions */}
                <tr>
                  <td style={{ padding: "14px 18px", fontWeight: 600, color: "#4b5563" }}>
                    Actions
                  </td>
                  <td style={{ padding: "14px 18px" }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button
                        onClick={() => navigate(`/trip/${t1.trip_id}`)}
                        style={{
                          padding: "6px 14px",
                          background: "#4f46e5",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor: "pointer",
                          fontSize: "0.85rem",
                          fontWeight: 600,
                        }}
                      >
                        Open Trip 1
                      </button>
                      <button
                        onClick={() => downloadTripPdf(t1.trip_id)}
                        style={{
                          padding: "6px 14px",
                          background: "#6b7280",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor: "pointer",
                          fontSize: "0.85rem",
                          fontWeight: 600,
                        }}
                      >
                        PDF
                      </button>
                    </div>
                  </td>
                  <td style={{ padding: "14px 18px" }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button
                        onClick={() => navigate(`/trip/${t2.trip_id}`)}
                        style={{
                          padding: "6px 14px",
                          background: "#4f46e5",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor: "pointer",
                          fontSize: "0.85rem",
                          fontWeight: 600,
                        }}
                      >
                        Open Trip 2
                      </button>
                      <button
                        onClick={() => downloadTripPdf(t2.trip_id)}
                        style={{
                          padding: "6px 14px",
                          background: "#6b7280",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor: "pointer",
                          fontSize: "0.85rem",
                          fontWeight: 600,
                        }}
                      >
                        PDF
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
