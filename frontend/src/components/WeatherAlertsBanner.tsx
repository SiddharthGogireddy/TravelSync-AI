import type { TripWeatherAlertsResponse, WeatherDisruptionAlert, DailyForecast } from "../services/weather";

interface Props {
  weatherData: TripWeatherAlertsResponse | null;
  loading?: boolean;
  error?: string | null;
}

export default function WeatherAlertsBanner({ weatherData, loading, error }: Props) {
  if (loading) {
    return (
      <div
        style={{
          padding: 16,
          background: "#f8fafc",
          borderRadius: 12,
          border: "1px solid #e2e8f0",
          color: "#64748b",
          fontSize: "0.9rem",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span style={{ fontSize: "1.2rem" }}>🌤️</span>
        <span>Fetching live meteorological forecasts and itinerary safety alerts...</span>
      </div>
    );
  }

  if (error && !weatherData) {
    return (
      <div
        style={{
          padding: 14,
          background: "#fef2f2",
          borderRadius: 10,
          border: "1px solid #fecaca",
          color: "#991b1b",
          fontSize: "0.88rem",
        }}
      >
        ⚠️ Live weather service is temporarily unavailable. Displaying trip default estimates.
      </div>
    );
  }

  if (!weatherData) return null;

  const { disruption_alerts, daily_forecasts, update_time, is_multi_destination } = weatherData;

  return (
    <div className="weather-alerts-container" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* 1. DISRUPTION ALERTS BANNER */}
      {disruption_alerts && disruption_alerts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {disruption_alerts.map((alert: WeatherDisruptionAlert, idx: number) => {
            const isSevere = alert.severity === "high" || alert.alert_type === "severe";
            const bg = isSevere ? "#fef2f2" : "#fffbeb";
            const border = isSevere ? "#fca5a5" : "#fcd34d";
            const titleColor = isSevere ? "#991b1b" : "#92400e";
            const badgeBg = isSevere ? "#fee2e2" : "#fef3c7";
            const badgeColor = isSevere ? "#b91c1c" : "#b45309";

            return (
              <div
                key={idx}
                className="weather-disruption-card"
                style={{
                  background: bg,
                  border: `1px solid ${border}`,
                  borderRadius: 12,
                  padding: "16px 20px",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.04)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: "1.3rem" }}>{isSevere ? "⛈️" : "⚠️"}</span>
                    <strong style={{ fontSize: "1rem", color: titleColor }}>{alert.title}</strong>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        padding: "2px 8px",
                        borderRadius: 12,
                        background: badgeBg,
                        color: badgeColor,
                        fontWeight: 600,
                      }}
                    >
                      Day {alert.day} • {alert.date}
                    </span>
                    {is_multi_destination && (
                      <span
                        style={{
                          fontSize: "0.72rem",
                          padding: "2px 8px",
                          borderRadius: 12,
                          background: "#e2e8f0",
                          color: "#334155",
                          fontWeight: 600,
                        }}
                      >
                        {alert.destination}
                      </span>
                    )}
                  </div>
                </div>

                <p style={{ margin: "0 0 10px", fontSize: "0.9rem", color: "#334155", lineHeight: 1.5 }}>
                  {alert.message}
                </p>

                {alert.affected_outdoor_activities && alert.affected_outdoor_activities.length > 0 && (
                  <div style={{ margin: "6px 0 10px", fontSize: "0.84rem", color: "#475569" }}>
                    <strong>Outdoor Sights on this Day:</strong>{" "}
                    {alert.affected_outdoor_activities.join(", ")}
                  </div>
                )}

                <div
                  style={{
                    background: "rgba(255,255,255,0.7)",
                    borderRadius: 8,
                    padding: "8px 12px",
                    borderLeft: `4px solid ${border}`,
                    fontSize: "0.82rem",
                    color: "#475569",
                  }}
                >
                  <strong>💡 Recommendation:</strong> {alert.recommendation}
                  <div style={{ marginTop: 4, fontStyle: "italic", fontSize: "0.76rem", color: "#64748b" }}>
                    Notice: TravelSync AI never modifies your confirmed saved itinerary automatically.
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 2. DAILY FORECASTS GRID */}
      {daily_forecasts && daily_forecasts.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: 12,
          }}
        >
          {daily_forecasts.map((f: DailyForecast, idx: number) => {
            const isAvailable = f.status === "available";

            return (
              <div
                key={idx}
                className="daily-forecast-card"
                style={{
                  background: isAvailable ? "#ffffff" : "#f8fafc",
                  border: isAvailable ? "1px solid #e2e8f0" : "1px dashed #cbd5e1",
                  borderRadius: 12,
                  padding: "14px 16px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: isAvailable ? "0 1px 3px rgba(0,0,0,0.05)" : "none",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#475569" }}>
                      Day {f.day} • {f.date.slice(5)}
                    </span>
                    {is_multi_destination && (
                      <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 500 }}>
                        {f.destination}
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "8px 0" }}>
                    <span style={{ fontSize: "1.8rem" }}>{f.icon || "🌤️"}</span>
                    <div>
                      <div style={{ fontSize: "0.88rem", fontWeight: 600, color: "#0f172a" }}>
                        {f.condition}
                      </div>
                      {isAvailable && f.min_temp != null && f.max_temp != null && (
                        <div style={{ fontSize: "0.82rem", color: "#475569" }}>
                          {Math.round(f.min_temp)}°C – {Math.round(f.max_temp)}°C
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {isAvailable ? (
                  <div
                    style={{
                      borderTop: "1px solid #f1f5f9",
                      paddingTop: 8,
                      marginTop: 6,
                      fontSize: "0.74rem",
                      color: "#64748b",
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>
                      🌧️ {f.precipitation_probability != null ? `${f.precipitation_probability}%` : "0%"}
                      {f.precipitation_sum ? ` (${f.precipitation_sum}mm)` : ""}
                    </span>
                    {f.wind_speed_max != null && (
                      <span>💨 {Math.round(f.wind_speed_max)} km/h</span>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: "0.74rem", color: "#94a3b8", fontStyle: "italic", marginTop: 4 }}>
                    {f.message || "Forecast unavailable beyond 16 days"}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 3. FOOTER ATTRIBUTION AND TIMESTAMPS */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 8,
          fontSize: "0.74rem",
          color: "#94a3b8",
          marginTop: 4,
        }}
      >
        <span>
          🌐 Meteorological data sourced from Open-Meteo • 16-day live window • Disruption thresholds analyzed by TravelSync AI
        </span>
        {update_time && (
          <span>Updated: {new Date(update_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        )}
      </div>
    </div>
  );
}
