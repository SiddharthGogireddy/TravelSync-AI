import { useEffect, useState } from "react";
import type { PlaceDetail } from "../services/api";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  initialPlace: {
    name: string;
    place_type?: string;
    category?: string;
    lat?: number;
    lon?: number;
    score?: number;
    description?: string;
    image_url?: string | null;
    opening_hours?: any;
    timing_status?: string;
    is_open_on_arrival?: boolean;
    distance_km?: number;
  } | null;
  details: PlaceDetail | null;
  loading: boolean;
  error: string | null;
}

export default function PlaceDetailModal({
  isOpen,
  onClose,
  initialPlace,
  details,
  loading,
  error,
}: Props) {
  const [imgError, setImgError] = useState(false);

  // Close on Escape key press
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Reset image error state when place changes
  useEffect(() => {
    setImgError(false);
  }, [initialPlace?.name, details?.image_url]);

  if (!isOpen || !initialPlace) return null;

  const placeType = details?.place_type || initialPlace.place_type || (initialPlace.category?.toLowerCase().includes("hotel") ? "hotel" : "attraction");
  const isHotel = placeType === "hotel";
  const name = details?.name || initialPlace.name;
  const category = details?.category || initialPlace.category || (isHotel ? "Accommodation" : "Attraction");
  const description = details?.description || initialPlace.description;
  const imageUrl = !imgError ? (details?.image_url || initialPlace.image_url) : null;
  const lat = details?.lat ?? initialPlace.lat;
  const lon = details?.lon ?? initialPlace.lon;
  const mapUrl = details?.map_url || (lat != null && lon != null ? `https://www.google.com/maps/search/?api=1&query=${lat},${lon}` : null);
  const openingHours = details?.opening_hours || initialPlace.opening_hours;

  const getCategoryIcon = () => {
    if (isHotel) return "🏨";
    const cat = category.toLowerCase();
    if (cat.includes("beach")) return "🏖️";
    if (cat.includes("museum") || cat.includes("gallery")) return "🏛️";
    if (cat.includes("park") || cat.includes("garden") || cat.includes("nature")) return "🌳";
    if (cat.includes("fort") || cat.includes("palace") || cat.includes("monument") || cat.includes("heritage")) return "🏰";
    if (cat.includes("temple") || cat.includes("church") || cat.includes("mosque")) return "🕌";
    if (cat.includes("food") || cat.includes("restaurant") || cat.includes("dining") || cat.includes("cafe")) return "🍽️";
    if (cat.includes("zoo") || cat.includes("wildlife")) return "🦁";
    return "📍";
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="place-detail-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "#ffffff",
          borderRadius: 14,
          maxWidth: 620,
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          display: "flex",
          flexDirection: "column",
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Media / Photo Banner */}
        <div style={{ position: "relative", width: "100%", height: 210, backgroundColor: "#0f172a", overflow: "hidden", borderTopLeftRadius: 14, borderTopRightRadius: 14 }}>
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={`Photo of ${name}`}
              onError={() => setImgError(true)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                background: isHotel
                  ? "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)"
                  : "linear-gradient(135deg, #312e81 0%, #6366f1 50%, #8b5cf6 100%)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
              }}
            >
              <span style={{ fontSize: "3rem", marginBottom: 6 }}>{getCategoryIcon()}</span>
              <span style={{ fontSize: "0.85rem", letterSpacing: "0.05em", textTransform: "uppercase", fontWeight: 600, opacity: 0.85 }}>
                {category}
              </span>
            </div>
          )}

          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            style={{
              position: "absolute",
              top: 12,
              right: 12,
              backgroundColor: "rgba(15, 23, 42, 0.75)",
              color: "#ffffff",
              border: "none",
              borderRadius: "50%",
              width: 32,
              height: 32,
              fontSize: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
              transition: "background 0.15s ease",
            }}
          >
            ✕
          </button>

          {/* Image Source Badge */}
          {details?.image_source && !imgError && (
            <span
              style={{
                position: "absolute",
                bottom: 8,
                right: 10,
                backgroundColor: "rgba(15, 23, 42, 0.7)",
                color: "#f8fafc",
                fontSize: "0.68rem",
                padding: "2px 8px",
                borderRadius: 4,
                fontWeight: 500,
              }}
            >
              Source: {details.image_source}
            </span>
          )}
        </div>

        {/* Modal Content */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Title & Badges */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
              <span
                style={{
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  padding: "3px 8px",
                  borderRadius: 6,
                  backgroundColor: isHotel ? "#e0f2fe" : "#ede9fe",
                  color: isHotel ? "#0369a1" : "#6d28d9",
                }}
              >
                {getCategoryIcon()} {category}
              </span>

              {initialPlace.distance_km != null && (
                <span style={{ fontSize: "0.74rem", color: "#64748b", fontWeight: 500 }}>
                  • {initialPlace.distance_km} km away
                </span>
              )}

              {loading && (
                <span style={{ fontSize: "0.74rem", color: "#6366f1", fontWeight: 600 }}>
                  [Loading rich details...]
                </span>
              )}
            </div>

            <h2 id="place-detail-title" style={{ margin: 0, fontSize: "1.35rem", color: "#0f172a", fontWeight: 700 }}>
              {name}
            </h2>

            {details?.address && (
              <p style={{ margin: "4px 0 0", fontSize: "0.82rem", color: "#64748b" }}>
                📍 {details.address}
              </p>
            )}

            {error && (
              <div style={{ marginTop: 8, padding: "8px 12px", background: "#fef2f2", color: "#991b1b", borderRadius: 6, fontSize: "0.8rem", border: "1px solid #fecaca" }}>
                ⚠️ {error} (showing baseline information)
              </div>
            )}
          </div>

          {/* Description */}
          {description && (
            <div style={{ fontSize: "0.88rem", color: "#334155", lineHeight: 1.5, background: "#f8fafc", padding: "12px 14px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
              {description}
            </div>
          )}

          {/* Ratings & Score Section */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
            {/* Provider rating */}
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "#fffbeb", border: "1px solid #fef3c7" }}>
              <div style={{ fontSize: "0.74rem", color: "#92400e", fontWeight: 600, textTransform: "uppercase" }}>
                Public Provider Rating
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#b45309", marginTop: 2 }}>
                {details?.provider_rating != null ? (
                  <>★ {details.provider_rating} / 5</>
                ) : (
                  <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "#78716c" }}>
                    No provider rating available
                  </span>
                )}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#78716c", marginTop: 2 }}>
                {details?.provider_rating_source ? `Source: ${details.provider_rating_source}` : "External public catalog"}
              </div>
            </div>

            {/* TravelSync Optimization / Match Score */}
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "#f0fdf4", border: "1px solid #dcfce7" }}>
              <div style={{ fontSize: "0.74rem", color: "#166534", fontWeight: 600, textTransform: "uppercase" }}>
                TravelSync Match Score
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#15803d", marginTop: 2 }}>
                {details?.travelsync_match_score != null || initialPlace.score != null ? (
                  <>🎯 {details?.travelsync_match_score ?? initialPlace.score} / 5</>
                ) : (
                  <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "#78716c" }}>
                    Standard itinerary stop
                  </span>
                )}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#78716c", marginTop: 2 }}>
                Traveler interest preference alignment
              </div>
            </div>
          </div>

          {/* Practical Visitor Information (Attractions / Dining) */}
          {!isHotel && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid #e2e8f0", paddingTop: 12 }}>
              <h4 style={{ margin: 0, fontSize: "0.92rem", color: "#0f172a", fontWeight: 600 }}>
                Practical Visitor Information
              </h4>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8, fontSize: "0.82rem" }}>
                {openingHours && (
                  <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                    <strong>Hours:</strong> {openingHours.display || `${openingHours.opens} - ${openingHours.closes}`}
                    {openingHours.closed_days?.length > 0 && (
                      <span style={{ display: "block", color: "#b91c1c", fontSize: "0.74rem", marginTop: 2 }}>
                        Closed on: {openingHours.closed_days.join(", ")}
                      </span>
                    )}
                  </div>
                )}

                {details?.estimated_visit_duration && (
                  <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                    <strong>Estimated Duration:</strong> {details.estimated_visit_duration}
                  </div>
                )}

                {details?.entry_fee && (
                  <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                    <strong>Entry Info:</strong> {details.entry_fee}
                  </div>
                )}

                {details?.best_time_to_visit && (
                  <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                    <strong>Best Time:</strong> {details.best_time_to_visit}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Hotel-Specific Details */}
          {isHotel && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid #e2e8f0", paddingTop: 12 }}>
              <h4 style={{ margin: 0, fontSize: "0.92rem", color: "#0f172a", fontWeight: 600 }}>
                Hotel & Lodging Details
              </h4>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8, fontSize: "0.82rem" }}>
                <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <strong>Property Type:</strong> {details?.star_rating || "Hotel Accommodation"}
                </div>
                <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <strong>Rate Estimate:</strong> {details?.price_per_night || "Check with property for live rates"}
                </div>
                <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <strong>Check-in:</strong> {details?.check_in_time || "02:00 PM (Standard)"}
                </div>
                <div style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0" }}>
                  <strong>Check-out:</strong> {details?.check_out_time || "11:00 AM (Standard)"}
                </div>
              </div>

              {/* Amenities */}
              {details?.amenities && details.amenities.length > 0 && (
                <div>
                  <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "#475569" }}>
                    Key Amenities:
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                    {details.amenities.map((am, aIdx) => (
                      <span
                        key={aIdx}
                        style={{
                          fontSize: "0.74rem",
                          padding: "2px 8px",
                          borderRadius: 12,
                          background: "#e2e8f0",
                          color: "#334155",
                          fontWeight: 500,
                        }}
                      >
                        ✓ {am}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <p style={{ margin: 0, fontSize: "0.72rem", color: "#94a3b8", fontStyle: "italic" }}>
                Note: Hotel rates, room categories, and availability are indicative and must be confirmed directly with the property.
              </p>
            </div>
          )}

          {/* Links & Map Button */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #e2e8f0", paddingTop: 14, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {mapUrl && (
                <a
                  href={mapUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    color: "#2563eb",
                    textDecoration: "none",
                    padding: "6px 12px",
                    borderRadius: 6,
                    background: "#eff6ff",
                    border: "1px solid #bfdbfe",
                  }}
                >
                  📍 Open in Google Maps ↗
                </a>
              )}

              {details?.website_url && (
                <a
                  href={details.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    color: "#4f46e5",
                    textDecoration: "none",
                    padding: "6px 12px",
                    borderRadius: 6,
                    background: "#eef2ff",
                    border: "1px solid #c7d2fe",
                  }}
                >
                  🌐 Reference Page ↗
                </a>
              )}
            </div>

            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "7px 18px",
                borderRadius: 6,
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                color: "#334155",
                fontSize: "0.84rem",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
