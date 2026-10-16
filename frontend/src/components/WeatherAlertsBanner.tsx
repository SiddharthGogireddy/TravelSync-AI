import type { TripWeatherAlertsResponse, WeatherDisruptionAlert, DailyForecast } from "../services/weather";
import {
  CloudSun,
  CloudRain,
  CloudLightning,
  AlertTriangle,
  Lightbulb,
  Wind,
  Globe,
  Sun,
  Cloud,
} from "lucide-react";

interface Props {
  weatherData: TripWeatherAlertsResponse | null;
  loading?: boolean;
  error?: string | null;
}

function getWeatherIcon(condition?: string) {
  const cond = (condition || "").toLowerCase();
  if (cond.includes("thunder") || cond.includes("storm") || cond.includes("lightning")) {
    return <CloudLightning size={24} style={{ color: "#ef4444" }} />;
  }
  if (cond.includes("rain") || cond.includes("shower") || cond.includes("drizzle")) {
    return <CloudRain size={24} style={{ color: "#38bdf8" }} />;
  }
  if (cond.includes("cloud") || cond.includes("overcast")) {
    return <Cloud size={24} style={{ color: "#94a3b8" }} />;
  }
  if (cond.includes("clear") || cond.includes("sun")) {
    return <Sun size={24} style={{ color: "#f59e0b" }} />;
  }
  return <CloudSun size={24} style={{ color: "var(--accent)" }} />;
}

export default function WeatherAlertsBanner({ weatherData, loading, error }: Props) {
  if (loading) {
    return (
      <div
        style={{
          padding: 16,
          background: "var(--code-bg)",
          borderRadius: 12,
          border: "1px solid var(--border)",
          color: "var(--text-muted)",
          fontSize: "0.9rem",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <CloudSun size={20} style={{ color: "var(--accent)" }} />
        <span>Fetching live meteorological forecasts and itinerary safety alerts...</span>
      </div>
    );
  }

  if (error && !weatherData) {
    return (
      <div
        style={{
          padding: 14,
          background: "rgba(239, 68, 68, 0.1)",
          borderRadius: 10,
          border: "1px solid rgba(239, 68, 68, 0.25)",
          color: "#ef4444",
          fontSize: "0.88rem",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <AlertTriangle size={16} />
        <span>Live weather service is temporarily unavailable. Displaying trip default estimates.</span>
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
            const bg = isSevere ? "rgba(239, 68, 68, 0.1)" : "rgba(245, 158, 11, 0.1)";
            const border = isSevere ? "rgba(239, 68, 68, 0.3)" : "rgba(245, 158, 11, 0.3)";
            const titleColor = isSevere ? "#ef4444" : "#f59e0b";
            const badgeBg = isSevere ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)";
            const badgeColor = isSevere ? "#ef4444" : "#f59e0b";

            return (
              <div
                key={idx}
                className="weather-disruption-card"
                style={{
                  background: bg,
                  border: `1px solid ${border}`,
                  borderRadius: 12,
                  padding: "16px 20px",
                  boxShadow: "var(--shadow)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {isSevere ? (
                      <CloudLightning size={20} style={{ color: "#ef4444" }} />
                    ) : (
                      <AlertTriangle size={20} style={{ color: "#f59e0b" }} />
                    )}
                    <strong style={{ fontSize: "1rem", color: titleColor }}>{alert.title}</strong>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        padding: "2px 8px",
                        borderRadius: 6,
                        background: badgeBg,
                        color: badgeColor,
                        fontWeight: 700,
                        textTransform: "uppercase",
                      }}
                    >
                      {alert.severity} priority
                    </span>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        padding: "2px 8px",
                        borderRadius: 6,
                        background: "var(--code-bg)",
                        color: "var(--text-secondary)",
                        fontWeight: 600,
                      }}
                    >
                      Day {alert.day} • {alert.date}
                    </span>
                  </div>
                </div>

                <p style={{ margin: "0 0 10px 0", fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                  {alert.message}
                </p>

                {alert.affected_outdoor_activities && alert.affected_outdoor_activities.length > 0 && (
                  <div style={{ marginBottom: 10, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    <span style={{ fontWeight: 600 }}>Potentially Impacted:</span>{" "}
                    {alert.affected_outdoor_activities.join(", ")}
                  </div>
                )}

                <div
                  style={{
                    background: "var(--card-bg)",
                    borderRadius: 8,
                    padding: "8px 12px",
                    borderLeft: `4px solid ${border}`,
                    fontSize: "0.82rem",
                    color: "var(--text-secondary)",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                  }}
                >
                  <Lightbulb size={16} style={{ color: "var(--accent)", flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <strong>Recommendation:</strong> {alert.recommendation}
                    <div style={{ marginTop: 4, fontStyle: "italic", fontSize: "0.76rem", color: "var(--text-muted)" }}>
                      Notice: TravelSync AI never modifies your confirmed saved itinerary automatically.
                    </div>
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
                  background: isAvailable ? "var(--card-bg)" : "var(--code-bg)",
                  border: isAvailable ? "1px solid var(--border)" : "1px dashed var(--border)",
                  borderRadius: 12,
                  padding: "14px 16px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: isAvailable ? "var(--shadow)" : "none",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)" }}>
                      Day {f.day} • {f.date.slice(5)}
                    </span>
                    {is_multi_destination && (
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 500 }}>
                        {f.destination}
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "8px 0" }}>
                    {getWeatherIcon(f.condition)}
                    <div>
                      <div style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--text-h)" }}>
                        {f.condition}
                      </div>
                      {isAvailable && f.min_temp != null && f.max_temp != null && (
                        <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                          {Math.round(f.min_temp)}°C – {Math.round(f.max_temp)}°C
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {isAvailable ? (
                  <div
                    style={{
                      borderTop: "1px solid var(--border)",
                      paddingTop: 8,
                      marginTop: 6,
                      fontSize: "0.74rem",
                      color: "var(--text-muted)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <CloudRain size={12} />
                      {f.precipitation_probability != null ? `${f.precipitation_probability}%` : "0%"}
                      {f.precipitation_sum ? ` (${f.precipitation_sum}mm)` : ""}
                    </span>
                    {f.wind_speed_max != null && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        <Wind size={12} />
                        {Math.round(f.wind_speed_max)} km/h
                      </span>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", fontStyle: "italic", marginTop: 4 }}>
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
          color: "var(--text-muted)",
          marginTop: 4,
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <Globe size={13} />
          <span>Meteorological data sourced from Open-Meteo • 16-day live window • Disruption thresholds analyzed by TravelSync AI</span>
        </span>
        {update_time && (
          <span>Updated: {new Date(update_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        )}
      </div>
    </div>
  );
}
