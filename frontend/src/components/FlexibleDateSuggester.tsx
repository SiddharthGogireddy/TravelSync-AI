import React, { useState } from "react";
import {
  CloudSun,
  Sun,
  CloudRain,
  Cloud,
  Thermometer,
  Sparkles,
  Check,
  AlertTriangle,
} from "lucide-react";
import { suggestTravelDates } from "../services/api";
import type { DateRecommendation, SuggestDatesResponse } from "../types/trip";

interface FlexibleDateSuggesterProps {
  destination: string;
  source?: string;
  initialDays?: number;
  travelers?: any[];
  onSelectDates: (startDate: string, endDate: string, duration: number) => void;
  currentStartDate?: string;
  currentEndDate?: string;
}

function renderWeatherIcon(condition?: string) {
  const cond = (condition || "").toLowerCase();
  if (cond.includes("rain") || cond.includes("shower") || cond.includes("storm")) {
    return <CloudRain size={20} style={{ color: "#38bdf8", flexShrink: 0 }} />;
  }
  if (cond.includes("cloud") || cond.includes("overcast")) {
    return <Cloud size={20} style={{ color: "#94a3b8", flexShrink: 0 }} />;
  }
  if (cond.includes("clear") || cond.includes("sun")) {
    return <Sun size={20} style={{ color: "#f59e0b", flexShrink: 0 }} />;
  }
  return <CloudSun size={20} style={{ color: "var(--accent)", flexShrink: 0 }} />;
}

export const FlexibleDateSuggester: React.FC<FlexibleDateSuggesterProps> = ({
  destination,
  source = "",
  initialDays = 3,
  travelers = [],
  onSelectDates,
  currentStartDate = "",
  currentEndDate = "",
}) => {
  const [days, setDays] = useState<number>(initialDays || 3);
  const [flexibleWindow, setFlexibleWindow] = useState<string>("next_month");
  const [earliestDate, setEarliestDate] = useState<string>("");
  const [latestDate, setLatestDate] = useState<string>("");
  const [weatherPref, setWeatherPref] = useState<string>("avoid_rain");
  const [preferWeekends, setPreferWeekends] = useState<boolean>(true);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [result, setResult] = useState<SuggestDatesResponse | null>(null);
  const [selectedWindowStart, setSelectedWindowStart] = useState<string>(currentStartDate);

  const handleSuggest = async () => {
    if (!destination.trim()) {
      setError("Please enter or select a destination first to evaluate weather suitability.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const resp = await suggestTravelDates({
        destination: destination.trim(),
        source: source.trim() || undefined,
        days: Number(days) || 3,
        flexible_window: flexibleWindow,
        earliest_date: earliestDate || undefined,
        latest_date: latestDate || undefined,
        weather_preference: weatherPref,
        prefer_weekends: preferWeekends,
        travelers_count: travelers.length || 1,
      });

      if (resp.success && resp.data) {
        setResult(resp.data);
      } else {
        setError("Unable to generate recommendations. Please try a different travel window.");
      }
    } catch (err: any) {
      setError(err?.detail || err?.message || "Failed to fetch date suggestions. Please check network connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyOption = (rec: DateRecommendation) => {
    setSelectedWindowStart(rec.start_date);
    onSelectDates(rec.start_date, rec.end_date, rec.duration_days);
  };

  return (
    <div
      style={{
        background: "var(--card-bg)",
        border: "1px solid var(--border)",
        borderRadius: "12px",
        padding: "18px",
        boxShadow: "var(--shadow)",
        marginTop: "12px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <CloudSun size={24} style={{ color: "var(--accent)" }} />
          <div>
            <h4 style={{ margin: 0, fontSize: "1.05rem", color: "var(--text-h)", fontWeight: 700 }}>
              AI Date Finder & Weather Ranking
            </h4>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-muted)" }}>
              Find the most pleasant travel window based on live meteorological forecasts & climate history.
            </p>
          </div>
        </div>
      </div>

      {/* Input Constraints */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
          background: "var(--code-bg)",
          padding: "14px",
          borderRadius: "8px",
          border: "1px solid var(--border)",
          marginBottom: "16px",
        }}
      >
        {/* Desired Duration */}
        <div>
          <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", marginBottom: "4px" }}>
            Trip Duration (Days)
          </label>
          <div style={{ display: "flex", gap: "6px", marginBottom: "6px" }}>
            {[3, 5, 7].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                style={{
                  padding: "4px 8px",
                  fontSize: "0.8rem",
                  borderRadius: "4px",
                  border: days === d ? "1px solid var(--accent)" : "1px solid var(--border)",
                  background: days === d ? "var(--accent-bg)" : "var(--card-bg)",
                  color: days === d ? "var(--accent)" : "var(--text-secondary)",
                  fontWeight: days === d ? 700 : 500,
                  cursor: "pointer",
                }}
              >
                {d} Days
              </button>
            ))}
          </div>
          <input
            type="number"
            min={1}
            max={30}
            value={days}
            onChange={(e) => setDays(Math.max(1, Math.min(30, Number(e.target.value) || 1)))}
            style={{
              padding: "6px 10px",
              fontSize: "0.88rem",
              borderRadius: "6px",
              border: "1px solid var(--input-border)",
              background: "var(--input-bg)",
              color: "var(--input-text)",
              width: "100%",
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Flexible Travel Window */}
        <div>
          <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", marginBottom: "4px" }}>
            Flexible Travel Window
          </label>
          <select
            value={flexibleWindow}
            onChange={(e) => setFlexibleWindow(e.target.value)}
            style={{
              padding: "7px 10px",
              fontSize: "0.85rem",
              borderRadius: "6px",
              border: "1px solid var(--input-border)",
              background: "var(--input-bg)",
              color: "var(--input-text)",
              width: "100%",
            }}
          >
            <option value="next_2_weeks">Next 2 Weeks (16-Day Live Forecast)</option>
            <option value="next_month">Next Month (Recommended)</option>
            <option value="next_6_weeks">Next 6 Weeks (Provisional Climate)</option>
            <option value="custom">Custom Date Horizon</option>
          </select>
        </div>

        {/* Weather Preference */}
        <div>
          <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", marginBottom: "4px" }}>
            Weather Preference
          </label>
          <select
            value={weatherPref}
            onChange={(e) => setWeatherPref(e.target.value)}
            style={{
              padding: "7px 10px",
              fontSize: "0.85rem",
              borderRadius: "6px",
              border: "1px solid var(--input-border)",
              background: "var(--input-bg)",
              color: "var(--input-text)",
              width: "100%",
            }}
          >
            <option value="avoid_rain">Avoid Rain (Sightseeing friendly)</option>
            <option value="mild">Comfortable & Mild Temperatures</option>
            <option value="any">Any Weather</option>
          </select>
        </div>

        {/* Weekend Preference */}
        <div>
          <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "var(--input-label)", marginBottom: "6px" }}>
            Timing Preference
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", color: "var(--text-secondary)", cursor: "pointer", marginTop: "8px" }}>
            <input
              type="checkbox"
              checked={preferWeekends}
              onChange={(e) => setPreferWeekends(e.target.checked)}
              style={{ width: "auto", margin: 0 }}
            />
            <span>Prefer Weekend Alignment (Fri – Sun)</span>
          </label>
        </div>
      </div>

      {/* Optional Custom Horizon bounds */}
      {flexibleWindow === "custom" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
          <div>
            <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: "4px" }}>
              Earliest Departure Date
            </label>
            <input
              type="date"
              value={earliestDate}
              onChange={(e) => setEarliestDate(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", width: "100%", boxSizing: "border-box" }}
            />
          </div>
          <div>
            <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--input-label)", display: "block", marginBottom: "4px" }}>
              Latest Return Date
            </label>
            <input
              type="date"
              value={latestDate}
              onChange={(e) => setLatestDate(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid var(--input-border)", background: "var(--input-bg)", color: "var(--input-text)", width: "100%", boxSizing: "border-box" }}
            />
          </div>
        </div>
      )}

      {/* Action Button */}
      <div style={{ display: "flex", justifyContent: "flex-start", alignItems: "center", gap: "10px" }}>
        <button
          type="button"
          onClick={handleSuggest}
          disabled={loading}
          style={{
            background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
            color: "#ffffff",
            padding: "9px 18px",
            borderRadius: "8px",
            border: "none",
            fontWeight: 600,
            fontSize: "0.9rem",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.75 : 1,
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            boxShadow: "0 2px 6px rgba(79, 70, 229, 0.3)",
          }}
        >
          {loading ? (
            <span>Analyzing Weather & Ranking Dates...</span>
          ) : (
            <>
              <Sparkles size={16} />
              <span>Suggest Best Travel Dates</span>
            </>
          )}
        </button>

        {destination && (
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Evaluating window for <strong>{destination}</strong> ({days} {days === 1 ? "day" : "days"})
          </span>
        )}
      </div>

      {error && (
        <div style={{ marginTop: "12px", padding: "10px 14px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "8px", color: "#ef4444", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px" }}>
          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Suggested Options List */}
      {result && result.recommendations && result.recommendations.length > 0 && (
        <div style={{ marginTop: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <h5 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-h)", fontWeight: 700 }}>
              Top Travel Windows for {result.destination}
            </h5>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              Evaluated {result.total_evaluated_windows} candidate windows
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
            {result.recommendations.map((rec, idx) => {
              const isSelected = (selectedWindowStart === rec.start_date || (currentStartDate === rec.start_date && currentEndDate === rec.end_date));
              const isVerified = rec.confidence === "forecast_verified";

              return (
                <div
                  key={idx}
                  style={{
                    background: isSelected ? "var(--accent-bg)" : "var(--card-bg)",
                    border: isSelected ? "2px solid var(--accent)" : "1px solid var(--border)",
                    borderRadius: "10px",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    boxShadow: isSelected ? "0 4px 12px rgba(99, 102, 241, 0.15)" : "var(--shadow)",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div>
                    {/* Header: Badge & Suitability */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          fontWeight: 700,
                          padding: "3px 8px",
                          borderRadius: "999px",
                          background: isSelected ? "var(--card-bg)" : "var(--code-bg)",
                          color: isSelected ? "var(--accent)" : "var(--text-secondary)",
                          border: "1px solid var(--border)",
                        }}
                      >
                        {rec.badge}
                      </span>
                      <span
                        style={{
                          fontSize: "0.82rem",
                          fontWeight: 700,
                          color: rec.suitability_score >= 80 ? "#10b981" : "#f59e0b",
                          background: rec.suitability_score >= 80 ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                          padding: "2px 8px",
                          borderRadius: "6px",
                        }}
                      >
                        {rec.suitability_score}/100 Match
                      </span>
                    </div>

                    {/* Date Range */}
                    <div style={{ fontSize: "1.02rem", fontWeight: 700, color: "var(--text-h)", marginBottom: "4px" }}>
                      {rec.date_display}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "10px" }}>
                      {rec.duration_days} Days ({rec.start_date} to {rec.end_date})
                    </div>

                    {/* Weather Outlook Pill */}
                    <div
                      style={{
                        background: "var(--code-bg)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        padding: "8px 10px",
                        marginBottom: "10px",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      {renderWeatherIcon(rec.weather_summary.condition)}
                      <div style={{ fontSize: "0.8rem", color: "var(--text-h)" }}>
                        <div style={{ fontWeight: 600 }}>{rec.weather_summary.condition}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.76rem", display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                          <Thermometer size={12} />
                          <span>{rec.weather_summary.avg_max_temp}°C / {rec.weather_summary.avg_min_temp}°C</span>
                          <span>•</span>
                          <CloudRain size={12} />
                          <span>{rec.weather_summary.rain_probability}% rain risk</span>
                        </div>
                      </div>
                    </div>

                    {/* Horizon / Confidence Notice */}
                    <div style={{ fontSize: "0.74rem", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ color: isVerified ? "#10b981" : "#f59e0b", fontWeight: 600 }}>
                        {isVerified ? "Live 16-Day Forecast" : "Provisional Seasonal Outlook"}
                      </span>
                    </div>

                    {/* Recommendation Reasons */}
                    <div style={{ marginBottom: "8px" }}>
                      <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                        Why this window:
                      </span>
                      <ul style={{ margin: "4px 0 0 0", paddingLeft: "18px", fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: "1.3" }}>
                        {rec.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Trade-offs */}
                    {rec.trade_offs && rec.trade_offs.length > 0 && (
                      <div style={{ marginBottom: "12px" }}>
                        <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                          Trade-offs to note:
                        </span>
                        <ul style={{ margin: "3px 0 0 0", paddingLeft: "18px", fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: "1.3" }}>
                          {rec.trade_offs.map((t, i) => (
                            <li key={i}>{t}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Selection Button */}
                  <button
                    type="button"
                    onClick={() => handleApplyOption(rec)}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: isSelected ? "1px solid var(--accent)" : "1px solid var(--border)",
                      background: isSelected ? "var(--accent)" : "var(--card-bg)",
                      color: isSelected ? "#ffffff" : "var(--text-secondary)",
                      fontWeight: 600,
                      fontSize: "0.86rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "6px",
                      marginTop: "6px",
                    }}
                  >
                    {isSelected ? (
                      <>
                        <Check size={14} />
                        <span>Dates Applied to Trip</span>
                      </>
                    ) : (
                      <span>Choose These Dates</span>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
