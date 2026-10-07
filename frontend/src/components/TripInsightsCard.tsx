import { useEffect, useState } from "react";
import { getTripInsights, type TripInsightsResponse } from "../services/api";

interface Props {
  tripId: string;
}

export default function TripInsightsCard({ tripId }: Props) {
  const [insights, setInsights] = useState<TripInsightsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadInsights() {
      setLoading(true);
      setError(null);
      try {
        const data = await getTripInsights(tripId);
        if (isMounted) {
          setInsights(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load insights");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (tripId) {
      loadInsights();
    }

    return () => {
      isMounted = false;
    };
  }, [tripId]);

  if (loading) {
    return (
      <div className="section card" style={{ padding: "24px", textAlign: "center" }}>
        <p style={{ margin: 0, color: "#6b7280" }}>Analyzing trip data and calculating insights...</p>
      </div>
    );
  }

  if (error || !insights) {
    return (
      <div className="section card" style={{ padding: "20px", color: "#dc2626" }}>
        <p style={{ margin: 0 }}>Unable to load trip analytics: {error ?? "No data"}</p>
      </div>
    );
  }

  const { metrics, observations, day_by_day_breakdown } = insights;

  const getObservationColor = (type: string) => {
    switch (type) {
      case "warning":
        return { bg: "#fef3c7", border: "#f59e0b", text: "#92400e", badge: "⚠️ Alert" };
      case "success":
        return { bg: "#ecfdf5", border: "#10b981", text: "#065f46", badge: "✅ Healthy" };
      default:
        return { bg: "#eff6ff", border: "#3b82f6", text: "#1e40af", badge: "💡 Insight" };
    }
  };

  const getUtilizationColor = (pct: number) => {
    if (pct > 100) return "#ef4444";
    if (pct >= 85) return "#f59e0b";
    return "#10b981";
  };

  return (
    <div
      className="section"
      style={{
        marginTop: "24px",
        marginBottom: "24px",
        textAlign: "left",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <h2 className="section-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
          📊 Trip Analytics & AI Insights
        </h2>
        <span
          style={{
            fontSize: "12px",
            background: "#ede9fe",
            color: "#6d28d9",
            padding: "4px 10px",
            borderRadius: "16px",
            fontWeight: 600,
          }}
        >
          {metrics.days} Days • {metrics.traveler_count} {metrics.traveler_count === 1 ? "Traveler" : "Travelers"}
        </span>
      </div>

      {/* Metrics Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Total Estimated Cost
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            ₹{metrics.total_trip_cost.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            Planned: ₹{metrics.planned_budget.toLocaleString()}
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Cost per Traveler
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            ₹{metrics.cost_per_traveler.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            Across {metrics.traveler_count} {metrics.traveler_count === 1 ? "person" : "people"}
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Cost per Day
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            ₹{metrics.cost_per_day.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            Across {metrics.days} days
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Budget Utilization
          </div>
          <div
            style={{
              fontSize: "22px",
              fontWeight: "bold",
              color: getUtilizationColor(metrics.budget_utilization_pct),
              marginTop: "4px",
            }}
          >
            {metrics.budget_utilization_pct}%
          </div>
          <div
            style={{
              width: "100%",
              height: "6px",
              background: "#e5e7eb",
              borderRadius: "3px",
              marginTop: "6px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${Math.min(metrics.budget_utilization_pct, 100)}%`,
                height: "100%",
                background: getUtilizationColor(metrics.budget_utilization_pct),
              }}
            />
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Itinerary Route
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            {metrics.distance} km
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            Total travel distance
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Attractions / Day
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            {metrics.attractions_per_day}
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            {metrics.total_attractions} total stops scheduled
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Avg Distance Between Stops
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            {metrics.average_distance_between_stops} km
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            Local transit average
          </div>
        </div>

        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            border: "1px solid #e5e7eb",
          }}
        >
          <div style={{ fontSize: "12px", color: "#6b7280", textTransform: "uppercase", fontWeight: 600 }}>
            Hotels & Lodging
          </div>
          <div style={{ fontSize: "22px", fontWeight: "bold", color: "#111827", marginTop: "4px" }}>
            {metrics.hotel_count}
          </div>
          <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>
            Recommended options
          </div>
        </div>
      </div>

      {/* Analytical Observations */}
      <div style={{ marginBottom: "20px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#374151", marginBottom: "12px" }}>
          Key Observations & Pacing Analysis
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {observations.map((obs, index) => {
            const styleMeta = getObservationColor(obs.type);
            return (
              <div
                key={index}
                style={{
                  padding: "12px 16px",
                  borderRadius: "8px",
                  backgroundColor: styleMeta.bg,
                  border: `1px solid ${styleMeta.border}`,
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ color: styleMeta.text, fontSize: "14px" }}>
                    {obs.title}
                  </strong>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      color: styleMeta.text,
                      background: "rgba(255, 255, 255, 0.6)",
                      padding: "2px 8px",
                      borderRadius: "12px",
                    }}
                  >
                    {styleMeta.badge}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: "13px", color: styleMeta.text, lineHeight: 1.4 }}>
                  {obs.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Day by Day Pacing Breakdown */}
      {day_by_day_breakdown.length > 0 && (
        <div
          style={{
            background: "white",
            padding: "16px",
            borderRadius: "10px",
            border: "1px solid #e5e7eb",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#374151", margin: "0 0 12px 0" }}>
            Daily Pacing & Sightseeing Distribution
          </h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb", color: "#6b7280", textAlign: "left" }}>
                  <th style={{ padding: "8px" }}>Day</th>
                  <th style={{ padding: "8px" }}>Attractions Scheduled</th>
                  <th style={{ padding: "8px" }}>Local Transit</th>
                  <th style={{ padding: "8px" }}>Pacing Intensity</th>
                </tr>
              </thead>
              <tbody>
                {day_by_day_breakdown.map((d) => (
                  <tr key={d.day} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "10px 8px", fontWeight: 600 }}>Day {d.day}</td>
                    <td style={{ padding: "10px 8px" }}>{d.attractions_count} stops</td>
                    <td style={{ padding: "10px 8px" }}>{d.travel_distance_km} km</td>
                    <td style={{ padding: "10px 8px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background:
                            d.attractions_count >= 4
                              ? "#fee2e2"
                              : d.attractions_count >= 2
                              ? "#fef3c7"
                              : "#ecfdf5",
                          color:
                            d.attractions_count >= 4
                              ? "#991b1b"
                              : d.attractions_count >= 2
                              ? "#92400e"
                              : "#065f46",
                        }}
                      >
                        {d.attractions_count >= 4
                          ? "Intensive"
                          : d.attractions_count >= 2
                          ? "Moderate"
                          : "Relaxed"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
