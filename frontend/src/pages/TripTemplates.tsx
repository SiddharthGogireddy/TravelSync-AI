import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import { getTemplates, createTripFromTemplate, deleteTemplate, getTemplate } from "../services/api";
import type { TripTemplate } from "../types/template";

export default function TripTemplates() {
  const [templates, setTemplates] = useState<TripTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  // State for Create Trip Modal
  const [activeTemplate, setActiveTemplate] = useState<TripTemplate | null>(null);
  const [customOrigin, setCustomOrigin] = useState("");
  const [customTravelMode, setCustomTravelMode] = useState("");
  const [customBudget, setCustomBudget] = useState<string>("");
  const [creatingTrip, setCreatingTrip] = useState(false);

  // State for Preview Structure Modal
  const [previewTemplate, setPreviewTemplate] = useState<TripTemplate | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const navigate = useNavigate();

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getTemplates();
      setTemplates(res.templates || []);
    } catch (err: any) {
      setError(err.message || "Failed to load templates");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleOpenCreateModal = (tpl: TripTemplate) => {
    setActiveTemplate(tpl);
    setCustomOrigin(tpl.source || "");
    setCustomTravelMode(tpl.travel_mode || "car");
    setCustomBudget(tpl.budget_summary?.total_budget ? String(tpl.budget_summary.total_budget) : "");
  };

  const handleConfirmCreateTrip = async () => {
    if (!activeTemplate) return;
    try {
      setCreatingTrip(true);
      const overrides: any = {};
      if (customOrigin.trim() && customOrigin.trim() !== activeTemplate.source) {
        overrides.source = customOrigin.trim();
      }
      if (customTravelMode && customTravelMode !== activeTemplate.travel_mode) {
        overrides.travel_mode = customTravelMode;
      }
      if (customBudget.trim()) {
        const b = parseFloat(customBudget);
        if (!isNaN(b) && b > 0) {
          overrides.budget = b;
        }
      }

      const res = await createTripFromTemplate(activeTemplate.id, overrides);
      alert(`Success! Created trip from template "${activeTemplate.name}".`);
      setActiveTemplate(null);
      navigate(`/trip/${res.trip_id}`);
    } catch (err: any) {
      alert(err.message || "Failed to create trip from template");
    } finally {
      setCreatingTrip(false);
    }
  };

  const handleOpenPreview = async (tpl: TripTemplate) => {
    try {
      setPreviewLoading(true);
      const fullTpl = await getTemplate(tpl.id);
      setPreviewTemplate(fullTpl);
    } catch {
      setPreviewTemplate(tpl);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDelete = async (templateId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete template "${name}"?`)) return;
    try {
      await deleteTemplate(templateId);
      setTemplates((prev) => prev.filter((t) => t.id !== templateId));
    } catch (err: any) {
      alert(err.message || "Failed to delete template");
    }
  };

  const categories = ["all", ...Array.from(new Set(templates.map((t) => t.category || "General")))];

  const filtered = templates.filter((tpl) => {
    const matchesSearch =
      tpl.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tpl.destination.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tpl.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tpl.preferences?.some((p) => p.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesCategory =
      selectedCategory === "all" || (tpl.category || "General").toLowerCase() === selectedCategory.toLowerCase();

    return matchesSearch && matchesCategory;
  });

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "20px 24px", fontFamily: "sans-serif" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.85rem", color: "var(--text-h)", fontWeight: 700 }}>
            Reusable Trip Templates
          </h1>
          <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: "0.95rem" }}>
            Start a new vacation instantly from proven itineraries without starting from scratch.
          </p>
        </div>
        <div style={{ background: "rgba(79, 70, 229, 0.15)", color: "var(--accent)", border: "1px solid var(--border)", padding: "8px 16px", borderRadius: 20, fontWeight: 600, fontSize: "0.88rem" }}>
          {templates.length} {templates.length === 1 ? "Template" : "Templates"} Available
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search by destination, name, or interest..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            flex: 1,
            minWidth: 260,
            padding: "10px 14px",
            border: "1px solid var(--input-border)",
            borderRadius: 8,
            fontSize: "0.92rem",
            background: "var(--input-bg)",
            color: "var(--input-text)",
            outline: "none",
          }}
        />

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          style={{
            padding: "10px 14px",
            border: "1px solid var(--input-border)",
            borderRadius: 8,
            background: "var(--input-bg)",
            fontSize: "0.92rem",
            color: "var(--input-text)",
            outline: "none",
          }}
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c === "all" ? "All Categories" : c}
            </option>
          ))}
        </select>
      </div>

      {/* Loading & Error States */}
      {loading && <p style={{ textAlign: "center", color: "#64748b", padding: 40 }}>Loading templates...</p>}
      {error && (
        <div style={{ background: "#fef2f2", color: "#b91c1c", padding: 14, borderRadius: 8, marginBottom: 20 }}>
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filtered.length === 0 && (
        <div
          style={{
            background: "#f8fafc",
            border: "2px dashed #cbd5e1",
            borderRadius: 12,
            padding: "48px 20px",
            textAlign: "center",
          }}
        >
          <h3 style={{ margin: "0 0 8px", color: "#1e293b" }}>
            {searchTerm || selectedCategory !== "all" ? "No matching templates found" : "No trip templates yet"}
          </h3>
          <p style={{ color: "#64748b", maxWidth: 480, margin: "0 auto 20px", fontSize: "0.92rem" }}>
            Convert any of your saved trips into a reusable template by clicking "Save as Template" inside the Trip View!
          </p>
          <button
            onClick={() => navigate("/trip-history")}
            style={{
              padding: "10px 20px",
              background: "#4f46e5",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Go to Trip History
          </button>
        </div>
      )}

      {/* Templates Grid */}
      {!loading && !error && filtered.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 20,
          }}
        >
          {filtered.map((tpl) => (
            <div
              key={tpl.id}
              style={{
                background: "var(--card-bg)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                boxShadow: "var(--card-shadow, 0 2px 4px rgba(0,0,0,0.03))",
                transition: "transform 0.15s, box-shadow 0.15s",
              }}
            >
              {/* Card Top: Category and Days badge */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    background: "var(--bg-alt)",
                    color: "var(--text-muted)",
                    border: "1px solid var(--border)",
                    padding: "3px 8px",
                    borderRadius: 6,
                  }}
                >
                  {tpl.category || "General"}
                </span>
                <span
                  style={{
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "#10b981",
                    fontWeight: 700,
                    fontSize: "0.8rem",
                    padding: "3px 10px",
                    borderRadius: 12,
                  }}
                >
                  {tpl.duration_days} {tpl.duration_days === 1 ? "Day" : "Days"}
                </span>
              </div>

              {/* Title & Destination */}
              <h3 style={{ margin: "0 0 6px", fontSize: "1.2rem", color: "var(--text-h)", fontWeight: 700 }}>
                {tpl.name}
              </h3>
              <div style={{ fontSize: "0.88rem", color: "var(--text-muted)", marginBottom: 8, display: "flex", gap: 6, alignItems: "center" }}>
                <span>{tpl.destination}</span>
                {tpl.source && <span>• from {tpl.source}</span>}
              </div>

              {tpl.description && (
                <p style={{ margin: "0 0 12px", color: "var(--text)", fontSize: "0.86rem", lineHeight: 1.4, flex: 1 }}>
                  {tpl.description}
                </p>
              )}

              {/* Key Planning Tags / Preferences */}
              {tpl.preferences && tpl.preferences.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                  {tpl.preferences.slice(0, 4).map((pref, i) => (
                    <span
                      key={i}
                      style={{
                        background: "rgba(124, 58, 237, 0.12)",
                        color: "#a78bfa",
                        fontSize: "0.75rem",
                        padding: "2px 8px",
                        borderRadius: 12,
                        fontWeight: 500,
                      }}
                    >
                      #{pref}
                    </span>
                  ))}
                  {tpl.preferences.length > 4 && (
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", alignSelf: "center" }}>
                      +{tpl.preferences.length - 4} more
                    </span>
                  )}
                </div>
              )}

              {/* Structure Stats */}
              <div
                style={{
                  background: "var(--bg-alt)",
                  borderRadius: 8,
                  padding: "10px 12px",
                  display: "flex",
                  justifyContent: "space-around",
                  marginBottom: 16,
                  fontSize: "0.82rem",
                  color: "var(--text)",
                  border: "1px solid var(--border)",
                }}
              >
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontWeight: 700, color: "var(--text-h)" }}>
                    {tpl.itinerary_structure?.places_count ?? 0}
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Places</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontWeight: 700, color: "var(--text-h)" }}>
                    {tpl.travel_mode ? tpl.travel_mode.toUpperCase() : "CAR"}
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Transport</div>
                </div>
                {tpl.budget_summary?.estimated_cost ? (
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontWeight: 700, color: "var(--text-h)" }}>
                      ₹{tpl.budget_summary.estimated_cost.toLocaleString()}
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Est. Cost</div>
                  </div>
                ) : null}
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                <button
                  onClick={() => handleOpenCreateModal(tpl)}
                  style={{
                    flex: 1,
                    padding: "9px 12px",
                    background: "var(--accent)",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 6,
                    fontWeight: 600,
                    fontSize: "0.86rem",
                    cursor: "pointer",
                  }}
                >
                  Use Template
                </button>

                <button
                  onClick={() => handleOpenPreview(tpl)}
                  style={{
                    padding: "9px 12px",
                    background: "var(--bg-alt)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    borderRadius: 6,
                    fontWeight: 600,
                    fontSize: "0.86rem",
                    cursor: "pointer",
                  }}
                  title="Preview structure and day schedule"
                >
                  Structure
                </button>

                <button
                  onClick={() => handleDelete(tpl.id, tpl.name)}
                  style={{
                    padding: "9px 12px",
                    background: "#fee2e2",
                    color: "#dc2626",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                    fontWeight: 600,
                    fontSize: "0.84rem",
                  }}
                  title="Delete template"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CREATE TRIP FROM TEMPLATE MODAL */}
      {activeTemplate && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "var(--card-bg)",
              borderRadius: 14,
              padding: 24,
              maxWidth: 500,
              width: "100%",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.3)",
              border: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
              <h2 style={{ margin: 0, fontSize: "1.35rem", color: "var(--text-h)" }}>
                Create Trip from Template
              </h2>
              <button
                onClick={() => setActiveTemplate(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  padding: 4,
                }}
              >
                <X size={18} />
              </button>
            </div>
            <p style={{ margin: "0 0 16px", color: "var(--text-muted)", fontSize: "0.88rem" }}>
              Template: <strong>{activeTemplate.name}</strong> ({activeTemplate.duration_days} days to {activeTemplate.destination})
            </p>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 4 }}>
                Origin City / Departure Point
              </label>
              <input
                type="text"
                value={customOrigin}
                onChange={(e) => setCustomOrigin(e.target.value)}
                placeholder="e.g. Hyderabad, Bengaluru"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--input-border)",
                  background: "var(--input-bg)",
                  color: "var(--input-text)",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 4 }}>
                Travel Mode
              </label>
              <select
                value={customTravelMode}
                onChange={(e) => setCustomTravelMode(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--input-border)",
                  background: "var(--input-bg)",
                  color: "var(--input-text)",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              >
                <option value="car">Car / Driving</option>
                <option value="flight">Flight</option>
                <option value="train">Train</option>
                <option value="bus">Bus</option>
              </select>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 4 }}>
                Budget (₹ INR, optional override)
              </label>
              <input
                type="number"
                value={customBudget}
                onChange={(e) => setCustomBudget(e.target.value)}
                placeholder="Leave blank to use template budget"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--input-border)",
                  background: "var(--input-bg)",
                  color: "var(--input-text)",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setActiveTemplate(null)}
                disabled={creatingTrip}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  background: "var(--bg-alt)",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                  color: "var(--text)",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmCreateTrip}
                disabled={creatingTrip}
                style={{
                  padding: "8px 18px",
                  borderRadius: 6,
                  border: "none",
                  background: "var(--accent)",
                  color: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                }}
              >
                {creatingTrip ? "Creating Trip..." : "Confirm & Create Trip"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PREVIEW STRUCTURE MODAL */}
      {previewTemplate && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "var(--card-bg)",
              borderRadius: 14,
              padding: 24,
              maxWidth: 600,
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.3)",
              border: "1px solid var(--border)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <h2 style={{ margin: "0 0 4px", fontSize: "1.3rem", color: "var(--text-h)" }}>
                  {previewTemplate.name}
                </h2>
                <div style={{ color: "var(--text-muted)", fontSize: "0.86rem" }}>
                  {previewTemplate.destination} • {previewTemplate.duration_days} Days
                </div>
              </div>
              <button
                onClick={() => setPreviewTemplate(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  padding: 4,
                }}
              >
                <X size={18} />
              </button>
            </div>

            {previewLoading ? (
              <p style={{ color: "var(--text-muted)" }}>Loading full structure...</p>
            ) : (
              <div>
                <h4 style={{ margin: "14px 0 8px", color: "var(--text-h)", fontSize: "0.95rem" }}>
                  Key Attractions & Activities
                </h4>
                {previewTemplate.itinerary_structure?.places_summary?.length ? (
                  <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
                    {previewTemplate.itinerary_structure.places_summary.map((p, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: "var(--bg-alt)",
                          padding: "8px 12px",
                          borderRadius: 6,
                          border: "1px solid var(--border)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          fontSize: "0.86rem",
                        }}
                      >
                        <span style={{ fontWeight: 600, color: "var(--text)" }}>{p.name}</span>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                          {p.category} ({p.duration_hours}h)
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.86rem" }}>No specific places registered.</p>
                )}

                <h4 style={{ margin: "14px 0 8px", color: "var(--text-h)", fontSize: "0.95rem" }}>
                  Day-by-Day Activity Count
                </h4>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
                  {Object.entries(previewTemplate.itinerary_structure?.schedule_outline || {}).map(([day, count]) => (
                    <div
                      key={day}
                      style={{
                        background: "rgba(124, 58, 237, 0.15)",
                        color: "#a78bfa",
                        padding: "6px 14px",
                        borderRadius: 8,
                        fontSize: "0.84rem",
                        fontWeight: 600,
                      }}
                    >
                      Day {day}: {count} activities
                    </div>
                  ))}
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                  <button
                    onClick={() => {
                      const t = previewTemplate;
                      setPreviewTemplate(null);
                      handleOpenCreateModal(t);
                    }}
                    style={{
                      padding: "8px 16px",
                      background: "var(--accent)",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      fontWeight: 600,
                      cursor: "pointer",
                      fontSize: "0.88rem",
                    }}
                  >
                    Use This Template
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
