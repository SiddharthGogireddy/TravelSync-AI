import { useEffect, useState } from "react";
import {
  Hotel,
  Palmtree,
  Landmark,
  Trees,
  Castle,
  Church,
  Utensils,
  Compass,
  MapPin,
  X,
  AlertTriangle,
  Star,
  Target,
  Check,
  ExternalLink,
  Globe,
} from "lucide-react";
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
    if (isHotel) return <Hotel size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    const cat = category.toLowerCase();
    if (cat.includes("beach")) return <Palmtree size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    if (cat.includes("museum") || cat.includes("gallery")) return <Landmark size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    if (cat.includes("park") || cat.includes("garden") || cat.includes("nature")) return <Trees size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    if (cat.includes("fort") || cat.includes("palace") || cat.includes("monument") || cat.includes("heritage")) return <Castle size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    if (cat.includes("temple") || cat.includes("church") || cat.includes("mosque")) return <Church size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    if (cat.includes("food") || cat.includes("restaurant") || cat.includes("dining") || cat.includes("cafe")) return <Utensils size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    if (cat.includes("zoo") || cat.includes("wildlife")) return <Compass size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
    return <MapPin size={14} style={{ display: "inline-block", verticalAlign: "middle" }} />;
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
          backgroundColor: "var(--card-bg)",
          borderRadius: 14,
          maxWidth: 620,
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "var(--shadow-lg)",
          border: "1px solid var(--border)",
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
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
              transition: "background 0.15s ease",
            }}
          >
            <X size={16} />
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
                  backgroundColor: isHotel ? "rgba(3, 105, 161, 0.15)" : "var(--accent-bg)",
                  color: isHotel ? "#0284c7" : "var(--accent)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {getCategoryIcon()} <span>{category}</span>
              </span>

              {initialPlace.distance_km != null && (
                <span style={{ fontSize: "0.74rem", color: "var(--text-muted)", fontWeight: 500 }}>
                  • {initialPlace.distance_km} km away
                </span>
              )}

              {loading && (
                <span style={{ fontSize: "0.74rem", color: "var(--accent)", fontWeight: 600 }}>
                  [Loading rich details...]
                </span>
              )}
            </div>

            <h2 id="place-detail-title" style={{ margin: 0, fontSize: "1.35rem", color: "var(--text-h)", fontWeight: 700 }}>
              {name}
            </h2>

            {details?.address && (
              <p style={{ margin: "4px 0 0", fontSize: "0.82rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 4 }}>
                <MapPin size={13} style={{ flexShrink: 0 }} />
                <span>{details.address}</span>
              </p>
            )}

            {error && (
              <div style={{ marginTop: 8, padding: "8px 12px", background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", borderRadius: 6, fontSize: "0.8rem", border: "1px solid rgba(239, 68, 68, 0.25)", display: "flex", alignItems: "center", gap: 6 }}>
                <AlertTriangle size={14} style={{ flexShrink: 0 }} />
                <span>{error} (showing baseline information)</span>
              </div>
            )}
          </div>

          {/* Description */}
          {description && (
            <div style={{ fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.5, background: "var(--code-bg)", padding: "12px 14px", borderRadius: 8, border: "1px solid var(--border)" }}>
              {description}
            </div>
          )}

          {/* Ratings & Score Section */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
            {/* Provider rating */}
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.25)" }}>
              <div style={{ fontSize: "0.74rem", color: "#f59e0b", fontWeight: 600, textTransform: "uppercase" }}>
                Public Provider Rating
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#f59e0b", marginTop: 2, display: "flex", alignItems: "center", gap: 4 }}>
                {details?.provider_rating != null ? (
                  <>
                    <Star size={15} style={{ fill: "#f59e0b", color: "#f59e0b" }} />
                    <span>{details.provider_rating} / 5</span>
                  </>
                ) : (
                  <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "var(--text-muted)" }}>
                    No provider rating available
                  </span>
                )}
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
                {details?.provider_rating_source ? `Source: ${details.provider_rating_source}` : "External public catalog"}
              </div>
            </div>

            {/* TravelSync Optimization / Match Score */}
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.25)" }}>
              <div style={{ fontSize: "0.74rem", color: "#10b981", fontWeight: 600, textTransform: "uppercase" }}>
                TravelSync Match Score
              </div>
              <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#10b981", marginTop: 2, display: "flex", alignItems: "center", gap: 4 }}>
                {details?.travelsync_match_score != null || initialPlace.score != null ? (
                  <>
                    <Target size={15} style={{ color: "#10b981" }} />
                    <span>{details?.travelsync_match_score ?? initialPlace.score} / 5</span>
                  </>
                ) : (
                  <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "var(--text-muted)" }}>
                    Standard itinerary stop
                  </span>
                )}
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
                Traveler interest preference alignment
              </div>
            </div>
          </div>

          {/* Practical Visitor Information (Attractions / Dining) */}
          {!isHotel && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <h4 style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-h)", fontWeight: 600 }}>
                Practical Visitor Information
              </h4>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8, fontSize: "0.82rem" }}>
                {openingHours && (
                  <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                    <strong>Hours:</strong> {openingHours.display || `${openingHours.opens} - ${openingHours.closes}`}
                    {openingHours.closed_days?.length > 0 && (
                      <span style={{ display: "block", color: "#ef4444", fontSize: "0.74rem", marginTop: 2 }}>
                        Closed on: {openingHours.closed_days.join(", ")}
                      </span>
                    )}
                  </div>
                )}

                {details?.estimated_visit_duration && (
                  <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                    <strong>Estimated Duration:</strong> {details.estimated_visit_duration}
                  </div>
                )}

                {details?.entry_fee && (
                  <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                    <strong>Entry Info:</strong> {details.entry_fee}
                  </div>
                )}

                {details?.best_time_to_visit && (
                  <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                    <strong>Best Time:</strong> {details.best_time_to_visit}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Hotel-Specific Details */}
          {isHotel && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <h4 style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-h)", fontWeight: 600 }}>
                Hotel & Lodging Details
              </h4>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8, fontSize: "0.82rem" }}>
                <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  <strong>Property Type:</strong> {details?.star_rating || "Hotel Accommodation"}
                </div>
                <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  <strong>Rate Estimate:</strong> {details?.price_per_night || "Check with property for live rates"}
                </div>
                <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  <strong>Check-in:</strong> {details?.check_in_time || "02:00 PM (Standard)"}
                </div>
                <div style={{ padding: "8px 12px", background: "var(--code-bg)", borderRadius: 6, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                  <strong>Check-out:</strong> {details?.check_out_time || "11:00 AM (Standard)"}
                </div>
              </div>

              {/* Amenities */}
              {details?.amenities && details.amenities.length > 0 && (
                <div>
                  <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--input-label)" }}>
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
                          background: "var(--code-bg)",
                          border: "1px solid var(--border)",
                          color: "var(--text-secondary)",
                          fontWeight: 500,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        <Check size={11} />
                        <span>{am}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                Note: Hotel rates, room categories, and availability are indicative and must be confirmed directly with the property.
              </p>
            </div>
          )}

          {/* Links & Map Button */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border)", paddingTop: 14, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {mapUrl && (
                <a
                  href={mapUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    color: "var(--accent)",
                    textDecoration: "none",
                    padding: "6px 12px",
                    borderRadius: 6,
                    background: "var(--accent-bg)",
                    border: "1px solid var(--accent-border)",
                  }}
                >
                  <MapPin size={14} />
                  <span>Open in Google Maps</span>
                  <ExternalLink size={12} />
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
                    gap: 6,
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    color: "var(--accent)",
                    textDecoration: "none",
                    padding: "6px 12px",
                    borderRadius: 6,
                    background: "var(--code-bg)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <Globe size={14} />
                  <span>Reference Page</span>
                  <ExternalLink size={12} />
                </a>
              )}
            </div>

            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "7px 18px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                background: "var(--card-bg)",
                color: "var(--text-secondary)",
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
