import { Link } from "react-router-dom";
import TripForm from "../components/TripForm";
import Results from "./Results";
import type { TripRequest } from "../types/trip";
import type { TripResponse } from "../types/api";

interface LandingPageProps {
  authStatus: { loggedIn: boolean; userId: string };
  onPlanTrip: (formData: TripRequest) => void;
  loading: boolean;
  errorMessage: string | null;
  lastRequest: TripRequest | null;
  data: TripResponse | null;
}

export default function LandingPage({
  authStatus,
  onPlanTrip,
  loading,
  errorMessage,
  lastRequest,
  data,
}: LandingPageProps) {
  const scrollToPlanner = () => {
    const el = document.getElementById("planner-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div style={{ color: "#0f172a", fontFamily: "inherit" }}>
      {/* Hero Section */}
      <section
        style={{
          background: "radial-gradient(ellipse at 50% 0%, #e0e7ff 0%, #f8fafc 70%, #ffffff 100%)",
          padding: "60px 24px 50px 24px",
          textAlign: "center",
          borderBottom: "1px solid #e2e8f0",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ maxWidth: 960, margin: "0 auto" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 16px",
              background: "#eef2ff",
              border: "1px solid #c7d2fe",
              borderRadius: "9999px",
              fontSize: "0.85rem",
              fontWeight: 700,
              color: "#4338ca",
              marginBottom: 20,
            }}
          >
            <span>✨</span> Next-Generation Travel Planning Powered by AI
          </div>

          <h1
            style={{
              fontSize: "clamp(2rem, 5vw, 3.25rem)",
              fontWeight: 800,
              lineHeight: 1.15,
              letterSpacing: "-0.03em",
              margin: "0 0 18px 0",
              color: "#0f172a",
            }}
          >
            Every Journey, Perfectly Planned &amp; Synchronized
          </h1>

          <p
            style={{
              fontSize: "clamp(1.05rem, 2vw, 1.25rem)",
              lineHeight: 1.6,
              color: "#475569",
              maxWidth: 720,
              margin: "0 auto 28px auto",
            }}
          >
            Generate intelligent multi-day itineraries in seconds. Adapt on the go with weather-aware
            replanning, smart routes, shared group expenses, and real-time team collaboration.
          </p>

          {/* Action CTAs */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 14,
              flexWrap: "wrap",
              marginBottom: 32,
            }}
          >
            <button
              onClick={scrollToPlanner}
              style={{
                padding: "13px 26px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)",
                color: "#ffffff",
                fontSize: "1rem",
                fontWeight: 700,
                border: "none",
                cursor: "pointer",
                boxShadow: "0 4px 14px rgba(79, 70, 229, 0.35)",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>🧭</span> Start Planning Free
            </button>

            {!authStatus.loggedIn ? (
              <Link
                to="/login"
                style={{
                  padding: "13px 24px",
                  borderRadius: "10px",
                  background: "#ffffff",
                  color: "#334155",
                  fontSize: "1rem",
                  fontWeight: 600,
                  border: "1px solid #cbd5e1",
                  textDecoration: "none",
                  boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                }}
              >
                Sign In
              </Link>
            ) : (
              <Link
                to="/trip-history"
                style={{
                  padding: "13px 24px",
                  borderRadius: "10px",
                  background: "#ffffff",
                  color: "#334155",
                  fontSize: "1rem",
                  fontWeight: 600,
                  border: "1px solid #cbd5e1",
                  textDecoration: "none",
                  boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                }}
              >
                View My Trips
              </Link>
            )}

            <Link
              to="/templates"
              style={{
                padding: "13px 22px",
                borderRadius: "10px",
                background: "transparent",
                color: "#4f46e5",
                fontSize: "0.95rem",
                fontWeight: 600,
                border: "1px solid transparent",
                textDecoration: "none",
              }}
            >
              Browse Templates →
            </Link>
          </div>

          {/* User state context badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 12,
              padding: "8px 18px",
              background: authStatus.loggedIn ? "#ecfdf5" : "#f1f5f9",
              border: `1px solid ${authStatus.loggedIn ? "#a7f3d0" : "#e2e8f0"}`,
              borderRadius: "9999px",
              fontSize: "0.85rem",
              color: authStatus.loggedIn ? "#065f46" : "#475569",
            }}
          >
            {authStatus.loggedIn ? (
              <span>
                👤 Signed in as <strong>{authStatus.userId.slice(0, 16)}...</strong> — Trips sync across your devices.
              </span>
            ) : (
              <span>
                👋 Browsing as <strong>Guest ({authStatus.userId.slice(0, 14)}...)</strong>.{" "}
                <Link to="/signup" style={{ color: "#4f46e5", fontWeight: 700, textDecoration: "underline" }}>
                  Create an account
                </Link>{" "}
                to save itineraries forever and invite collaborators.
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section style={{ padding: "50px 24px 60px 24px", maxWidth: 1140, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h2 style={{ fontSize: "1.85rem", fontWeight: 800, color: "#0f172a", margin: "0 0 10px 0" }}>
            Everything You Need for Effortless Journeys
          </h2>
          <p style={{ fontSize: "1.02rem", color: "#64748b", margin: 0 }}>
            Powered by advanced AI planning models and real-time travel APIs
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: 24,
          }}
        >
          {/* Card 1 */}
          <div
            style={{
              padding: "26px",
              background: "#ffffff",
              borderRadius: "14px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>🤖</div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
              AI Itinerary Planning
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b", lineHeight: 1.5 }}>
              Generates customized daily schedules tuned to your selected pacing, dietary preferences,
              accessibility needs, and attraction opening hours.
            </p>
          </div>

          {/* Card 2 */}
          <div
            style={{
              padding: "26px",
              background: "#ffffff",
              borderRadius: "14px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>🌦️</div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
              Weather-Aware Replanning
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b", lineHeight: 1.5 }}>
              Live forecast detection and rain alerts. Automatically suggests indoor museum and cafe swaps
              when bad weather threatens your outdoor plans.
            </p>
          </div>

          {/* Card 3 */}
          <div
            style={{
              padding: "26px",
              background: "#ffffff",
              borderRadius: "14px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>🗺️</div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
              Multi-Modal Smart Routes
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b", lineHeight: 1.5 }}>
              Optimized turn-by-turn driving, walking, and transit navigation. Calculates realistic commute times
              so you spend more time enjoying and less time commuting.
            </p>
          </div>

          {/* Card 4 */}
          <div
            style={{
              padding: "26px",
              background: "#ffffff",
              borderRadius: "14px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>💳</div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
              Budgeting &amp; Group Expenses
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b", lineHeight: 1.5 }}>
              Track costs in any currency, view categorized expense breakdown charts, and settle shared debts
              fairly with group split-bill calculations.
            </p>
          </div>

          {/* Card 5 */}
          <div
            style={{
              padding: "26px",
              background: "#ffffff",
              borderRadius: "14px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>👥</div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
              Shared Trips &amp; Roles
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b", lineHeight: 1.5 }}>
              Collaborate seamlessly with your travel companions. Secure invitations with Owner, Editor,
              and Viewer role permissions, live chat, and shared trip journals.
            </p>
          </div>

          {/* Card 6 */}
          <div
            style={{
              padding: "26px",
              background: "#ffffff",
              borderRadius: "14px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>📲</div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
              Offline PWA Experience
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b", lineHeight: 1.5 }}>
              Installable directly on desktop and mobile. Cached itineraries ensure your schedule is always
              accessible even at 35,000 feet without cellular service.
            </p>
          </div>
        </div>
      </section>

      {/* Interactive Planner Section */}
      <section
        id="planner-section"
        style={{
          background: "#f8fafc",
          borderTop: "1px solid #e2e8f0",
          padding: "60px 20px 80px 20px",
        }}
      >
        <div style={{ maxWidth: 880, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <span
              style={{
                fontSize: "0.82rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "#4f46e5",
              }}
            >
              Ready to travel?
            </span>
            <h2 style={{ fontSize: "2rem", fontWeight: 800, color: "#0f172a", margin: "8px 0 10px 0" }}>
              Plan Your Adventure in Minutes
            </h2>
            <p style={{ fontSize: "0.98rem", color: "#64748b", margin: 0 }}>
              Enter your destination, dates, and budget below. TravelSync AI will craft your synchronized itinerary.
            </p>
          </div>

          <div style={{ marginBottom: 32 }}>
            <TripForm onSubmit={onPlanTrip} />
          </div>

          {/* Error Message with Retry Button */}
          {errorMessage && (
            <div
              role="alert"
              style={{
                maxWidth: 680,
                margin: "0 auto 24px auto",
                padding: "16px 20px",
                background: "#fee2e2",
                border: "1px solid #f87171",
                borderRadius: 10,
                color: "#991b1b",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 14,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: "1.2rem" }}>⚠️</span>
                <span style={{ fontSize: "0.95rem", lineHeight: 1.4 }}>{errorMessage}</span>
              </div>
              {lastRequest && (
                <button
                  onClick={() => onPlanTrip(lastRequest)}
                  disabled={loading}
                  style={{
                    padding: "8px 16px",
                    background: "#b91c1c",
                    color: "#fff",
                    border: "none",
                    borderRadius: 8,
                    fontWeight: 700,
                    cursor: "pointer",
                    fontSize: "0.85rem",
                    whiteSpace: "nowrap",
                  }}
                >
                  Retry Planning
                </button>
              )}
            </div>
          )}

          {loading && (
            <div style={{ textAlign: "center", padding: "30px 0", color: "#4f46e5" }}>
              <div style={{ fontSize: "2rem", marginBottom: 8 }}>✈️</div>
              <p style={{ fontWeight: 600, fontSize: "1.05rem" }}>
                AI is generating your customized itinerary...
              </p>
            </div>
          )}

          {data && <Results data={data} />}
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          background: "#0f172a",
          color: "#94a3b8",
          padding: "40px 24px 30px 24px",
          borderTop: "1px solid #1e293b",
        }}
      >
        <div
          style={{
            maxWidth: 1140,
            margin: "0 auto",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 20,
          }}
        >
          <div>
            <div style={{ color: "#ffffff", fontWeight: 700, fontSize: "1.1rem", marginBottom: 4 }}>
              ✈️ TravelSync AI
            </div>
            <div style={{ fontSize: "0.85rem" }}>
              Intelligent multi-modal trip planning &amp; synchronized group travel.
            </div>
          </div>

          <div style={{ display: "flex", gap: 20, flexWrap: "wrap", fontSize: "0.88rem" }}>
            <Link to="/templates" style={{ color: "#cbd5e1", textDecoration: "none" }}>
              Templates
            </Link>
            <Link to="/compare" style={{ color: "#cbd5e1", textDecoration: "none" }}>
              Compare Trips
            </Link>
            <Link to="/load-trip" style={{ color: "#cbd5e1", textDecoration: "none" }}>
              Load Trip
            </Link>
            <Link to="/trip-history" style={{ color: "#cbd5e1", textDecoration: "none" }}>
              Trip History
            </Link>
            {!authStatus.loggedIn ? (
              <Link to="/login" style={{ color: "#818cf8", textDecoration: "none", fontWeight: 600 }}>
                Sign In
              </Link>
            ) : (
              <Link to="/trip-history" style={{ color: "#818cf8", textDecoration: "none", fontWeight: 600 }}>
                My Account
              </Link>
            )}
          </div>
        </div>

        <div
          style={{
            maxWidth: 1140,
            margin: "24px auto 0 auto",
            paddingTop: 20,
            borderTop: "1px solid #1e293b",
            fontSize: "0.8rem",
            color: "#64748b",
            textAlign: "center",
          }}
        >
          © {new Date().getFullYear()} TravelSync AI. All rights reserved. Built with privacy-first offline caching and verified JWT security.
        </div>
      </footer>
    </div>
  );
}
