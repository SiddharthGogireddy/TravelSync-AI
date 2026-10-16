import { Link } from "react-router-dom";
import {
  Sparkles,
  Compass,
  Bot,
  CloudSun,
  Map,
  CreditCard,
  Users,
  Smartphone,
  User,
  UserCheck,
  AlertTriangle,
  Loader2,
} from "lucide-react";
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
    <div style={{ color: "var(--text-primary)", fontFamily: "inherit" }}>
      {/* Hero Section */}
      <section
        style={{
          background: "radial-gradient(ellipse at 50% 0%, var(--accent-bg) 0%, var(--bg) 70%, var(--card-bg) 100%)",
          padding: "60px 24px 50px 24px",
          textAlign: "center",
          borderBottom: "1px solid var(--border)",
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
              background: "var(--accent-bg)",
              border: "1px solid var(--accent-border)",
              borderRadius: "9999px",
              fontSize: "0.85rem",
              fontWeight: 700,
              color: "var(--accent)",
              marginBottom: 20,
            }}
          >
            <Sparkles size={16} />
            <span>Next-Generation Travel Planning Powered by AI</span>
          </div>

          <h1
            style={{
              fontSize: "clamp(2rem, 5vw, 3.25rem)",
              fontWeight: 800,
              lineHeight: 1.15,
              letterSpacing: "-0.03em",
              margin: "0 0 18px 0",
              color: "var(--text-h)",
            }}
          >
            Every Journey, Perfectly Planned &amp; Synchronized
          </h1>

          <p
            style={{
              fontSize: "clamp(1.05rem, 2vw, 1.25rem)",
              lineHeight: 1.6,
              color: "var(--text-muted)",
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
              <Compass size={18} />
              <span>Start Planning Free</span>
            </button>

            {!authStatus.loggedIn ? (
              <Link
                to="/login"
                style={{
                  padding: "13px 24px",
                  borderRadius: "10px",
                  background: "var(--card-bg)",
                  color: "var(--text-secondary)",
                  fontSize: "1rem",
                  fontWeight: 600,
                  border: "1px solid var(--border)",
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
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
                  background: "var(--card-bg)",
                  color: "var(--text-secondary)",
                  fontSize: "1rem",
                  fontWeight: 600,
                  border: "1px solid var(--border)",
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                My Trips
              </Link>
            )}
          </div>

          {/* Trust / PWA Badges */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 20,
              fontSize: "0.86rem",
              color: "var(--text-muted)",
              flexWrap: "wrap",
              marginBottom: 28,
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: 700 }}>•</span> Offline-Ready PWA
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: 700 }}>•</span> Live Meteorological Forecasts
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: "#10b981", fontWeight: 700 }}>•</span> Multi-Currency Group Splitting
            </span>
          </div>

          {/* User / Session State Card */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 18px",
              background: "var(--code-bg)",
              border: "1px solid var(--border)",
              borderRadius: "9999px",
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
            }}
          >
            {authStatus.loggedIn ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <User size={14} style={{ color: "var(--accent)" }} />
                <span>
                  Signed in as <strong>{authStatus.userId.slice(0, 16)}...</strong> — Trips sync across your devices.
                </span>
              </span>
            ) : (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <UserCheck size={14} style={{ color: "var(--accent)" }} />
                <span>
                  Browsing as <strong>Guest ({authStatus.userId.slice(0, 14)}...)</strong>.{" "}
                  <Link to="/signup" style={{ color: "var(--accent)", fontWeight: 700, textDecoration: "underline" }}>
                    Create an account
                  </Link>{" "}
                  to save itineraries forever and invite collaborators.
                </span>
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section style={{ padding: "50px 24px 60px 24px", maxWidth: 1140, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h2 style={{ fontSize: "1.85rem", fontWeight: 800, color: "var(--text-h)", margin: "0 0 10px 0" }}>
            Everything You Need for Effortless Journeys
          </h2>
          <p style={{ fontSize: "1.02rem", color: "var(--text-muted)", margin: 0 }}>
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
              background: "var(--card-bg)",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ marginBottom: 14 }}>
              <Bot size={28} style={{ color: "var(--accent)" }} />
            </div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
              AI Itinerary Planning
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Generates customized daily schedules tuned to your selected pacing, dietary preferences,
              accessibility needs, and attraction opening hours.
            </p>
          </div>

          {/* Card 2 */}
          <div
            style={{
              padding: "26px",
              background: "var(--card-bg)",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ marginBottom: 14 }}>
              <CloudSun size={28} style={{ color: "var(--accent)" }} />
            </div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
              Weather-Aware Replanning
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Live forecast detection and rain alerts. Automatically suggests indoor museum and cafe swaps
              when bad weather threatens your outdoor plans.
            </p>
          </div>

          {/* Card 3 */}
          <div
            style={{
              padding: "26px",
              background: "var(--card-bg)",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ marginBottom: 14 }}>
              <Map size={28} style={{ color: "var(--accent)" }} />
            </div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
              Multi-Modal Smart Routes
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Optimized turn-by-turn driving, walking, and transit navigation. Calculates realistic commute times
              so you spend more time enjoying and less time commuting.
            </p>
          </div>

          {/* Card 4 */}
          <div
            style={{
              padding: "26px",
              background: "var(--card-bg)",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ marginBottom: 14 }}>
              <CreditCard size={28} style={{ color: "var(--accent)" }} />
            </div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
              Budgeting &amp; Group Expenses
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Track costs in any currency, view categorized expense breakdown charts, and settle shared debts
              fairly with group split-bill calculations.
            </p>
          </div>

          {/* Card 5 */}
          <div
            style={{
              padding: "26px",
              background: "var(--card-bg)",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ marginBottom: 14 }}>
              <Users size={28} style={{ color: "var(--accent)" }} />
            </div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
              Shared Trips &amp; Roles
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              Collaborate seamlessly with your travel companions. Secure invitations with Owner, Editor,
              and Viewer role permissions, live chat, and shared trip journals.
            </p>
          </div>

          {/* Card 6 */}
          <div
            style={{
              padding: "26px",
              background: "var(--card-bg)",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ marginBottom: 14 }}>
              <Smartphone size={28} style={{ color: "var(--accent)" }} />
            </div>
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
              Offline PWA Experience
            </h3>
            <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
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
          background: "var(--bg)",
          borderTop: "1px solid var(--border)",
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
                color: "var(--accent)",
              }}
            >
              Ready to travel?
            </span>
            <h2 style={{ fontSize: "2rem", fontWeight: 800, color: "var(--text-h)", margin: "8px 0 10px 0" }}>
              Plan Your Adventure in Minutes
            </h2>
            <p style={{ fontSize: "0.98rem", color: "var(--text-muted)", margin: 0 }}>
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
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: 10,
                color: "#ef4444",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 14,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <AlertTriangle size={18} style={{ color: "#ef4444", flexShrink: 0 }} />
                <span style={{ fontSize: "0.95rem", lineHeight: 1.4 }}>{errorMessage}</span>
              </div>
              {lastRequest && (
                <button
                  onClick={() => onPlanTrip(lastRequest)}
                  disabled={loading}
                  style={{
                    padding: "8px 16px",
                    background: "#ef4444",
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
            <div style={{ textAlign: "center", padding: "30px 0", color: "var(--accent)" }}>
              <div style={{ marginBottom: 8, display: "flex", justifyContent: "center" }}>
                <Loader2 size={32} style={{ animation: "spin 1s linear infinite" }} />
              </div>
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
          background: "var(--nav-bg)",
          color: "var(--text-muted)",
          padding: "40px 24px 30px 24px",
          borderTop: "1px solid var(--nav-border)",
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
            <div style={{ color: "var(--text-h)", fontWeight: 700, fontSize: "1.1rem", marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
              <Compass size={18} style={{ color: "var(--accent)" }} />
              <span>TravelSync AI</span>
            </div>
            <div style={{ fontSize: "0.85rem" }}>
              Intelligent multi-modal trip planning &amp; synchronized group travel.
            </div>
          </div>

          <div style={{ display: "flex", gap: 20, flexWrap: "wrap", fontSize: "0.88rem" }}>
            <Link to="/templates" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>
              Templates
            </Link>
            <Link to="/compare" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>
              Compare Trips
            </Link>
            <Link to="/load-trip" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>
              Load Trip
            </Link>
            <Link to="/trip-history" style={{ color: "var(--text-secondary)", textDecoration: "none" }}>
              Trip History
            </Link>
            {!authStatus.loggedIn ? (
              <Link to="/login" style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}>
                Sign In
              </Link>
            ) : (
              <Link to="/trip-history" style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}>
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
            borderTop: "1px solid var(--border)",
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            textAlign: "center",
          }}
        >
          &copy; {new Date().getFullYear()} TravelSync AI. All rights reserved. Built with privacy-first offline caching and verified JWT security.
        </div>
      </footer>
    </div>
  );
}
