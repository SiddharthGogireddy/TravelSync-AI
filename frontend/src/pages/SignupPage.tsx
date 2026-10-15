import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  apiRegister,
  apiClaimSession,
  getOrCreateUserId,
  isAuthenticated,
} from "../services/identity";

interface SignupPageProps {
  onAuthSuccess?: () => void;
}

export default function SignupPage({ onAuthSuccess }: SignupPageProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = searchParams.get("redirect") || "/trip-history";
  const claimParam = searchParams.get("claim");

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [claimGuestSession, setClaimGuestSession] = useState<boolean>(() => {
    return claimParam === "true" || true;
  });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const currentGuestId = getOrCreateUserId();
  const hasGuestSession = Boolean(currentGuestId && currentGuestId.startsWith("user_"));
  const alreadyLoggedIn = isAuthenticated();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password || password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match. Please re-enter your password.");
      return;
    }

    setLoading(true);

    try {
      if (hasGuestSession && claimGuestSession) {
        // Safe claiming: preserves all guest trips under currentGuestId
        await apiClaimSession(cleanEmail, password, fullName.trim() || undefined);
        setSuccessMessage("Account created! All your guest trips have been permanently linked to your account.");
      } else {
        // Fresh account registration
        await apiRegister(cleanEmail, password, fullName.trim() || undefined);
        setSuccessMessage("Account created successfully! Welcome to TravelSync AI.");
      }

      onAuthSuccess?.();

      setTimeout(() => {
        navigate(redirectTarget);
      }, 700);
    } catch (err: any) {
      console.error("Signup error:", err);
      if (err?.message?.includes("409") || err?.message?.toLowerCase().includes("already registered") || err?.message?.toLowerCase().includes("already claimed")) {
        setErrorMessage("An account with this email address already exists. Please sign in instead.");
      } else if (err?.message?.includes("422")) {
        setErrorMessage(err?.message || "Invalid registration details. Please verify your entries.");
      } else if (err?.message?.includes("429")) {
        setErrorMessage("Too many registration attempts. Please wait a moment before trying again.");
      } else {
        setErrorMessage(err?.message || "Failed to create account. Please check your connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      style={{
        minHeight: "85vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px 16px",
        background: "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 100%)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "480px",
          background: "#ffffff",
          borderRadius: "16px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
          border: "1px solid #e2e8f0",
          padding: "36px 32px",
          boxSizing: "border-box",
        }}
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "26px" }}>
          <Link
            to="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              textDecoration: "none",
              color: "#4f46e5",
              fontWeight: 800,
              fontSize: "1.35rem",
              letterSpacing: "-0.02em",
            }}
          >
            <span style={{ fontSize: "1.6rem" }}>✈️</span> TravelSync AI
          </Link>
          <h1
            style={{
              margin: "16px 0 6px 0",
              fontSize: "1.6rem",
              fontWeight: 700,
              color: "#0f172a",
            }}
          >
            Create Your Account
          </h1>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b" }}>
            Start planning smart AI itineraries and collaborate with your travel group
          </p>
        </div>

        {alreadyLoggedIn && (
          <div
            style={{
              marginBottom: "20px",
              padding: "12px 14px",
              background: "#ecfdf5",
              border: "1px solid #a7f3d0",
              borderRadius: "10px",
              color: "#065f46",
              fontSize: "0.88rem",
            }}
          >
            You are already logged in. Creating a new account will switch your active session.
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div
            role="alert"
            style={{
              marginBottom: "20px",
              padding: "12px 14px",
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: "10px",
              color: "#b91c1c",
              fontSize: "0.88rem",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span>⚠️</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Success Alert */}
        {successMessage && (
          <div
            role="status"
            style={{
              marginBottom: "20px",
              padding: "12px 14px",
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              borderRadius: "10px",
              color: "#166534",
              fontSize: "0.88rem",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span>✅</span>
            <span>{successMessage}</span>
          </div>
        )}

        {/* Guest Session Preserving Card */}
        {hasGuestSession && (
          <div
            style={{
              marginBottom: "22px",
              padding: "14px",
              background: "#f8fafc",
              border: "1px solid #cbd5e1",
              borderRadius: "12px",
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                cursor: "pointer",
                userSelect: "none",
              }}
            >
              <input
                type="checkbox"
                checked={claimGuestSession}
                onChange={(e) => setClaimGuestSession(e.target.checked)}
                style={{
                  marginTop: 3,
                  width: 17,
                  height: 17,
                  accentColor: "#4f46e5",
                  cursor: "pointer",
                }}
              />
              <div>
                <strong style={{ display: "block", color: "#1e293b", fontSize: "0.9rem" }}>
                  Preserve and link my existing guest trips
                </strong>
                <span style={{ fontSize: "0.82rem", color: "#64748b", lineHeight: 1.4 }}>
                  Active guest session: <code style={{ color: "#334155" }}>{currentGuestId.slice(0, 18)}...</code>.
                  Keep checked so any trips you planned as a guest transfer ownership directly to your new account.
                </span>
              </div>
            </label>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSignup} noValidate>
          <div style={{ marginBottom: "16px" }}>
            <label
              htmlFor="signup-name"
              style={{
                display: "block",
                marginBottom: "6px",
                fontSize: "0.88rem",
                fontWeight: 600,
                color: "#334155",
              }}
            >
              Full Name <span style={{ color: "#94a3b8", fontWeight: 400 }}>(Optional)</span>
            </label>
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Morgan"
              disabled={loading}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "11px 14px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                fontSize: "0.95rem",
                color: "#0f172a",
                outline: "none",
                transition: "border-color 0.2s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#4f46e5")}
              onBlur={(e) => (e.target.style.borderColor = "#cbd5e1")}
            />
          </div>

          <div style={{ marginBottom: "16px" }}>
            <label
              htmlFor="signup-email"
              style={{
                display: "block",
                marginBottom: "6px",
                fontSize: "0.88rem",
                fontWeight: 600,
                color: "#334155",
              }}
            >
              Email Address <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={loading}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "11px 14px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                fontSize: "0.95rem",
                color: "#0f172a",
                outline: "none",
                transition: "border-color 0.2s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#4f46e5")}
              onBlur={(e) => (e.target.style.borderColor = "#cbd5e1")}
            />
          </div>

          <div style={{ marginBottom: "16px" }}>
            <label
              htmlFor="signup-password"
              style={{
                display: "block",
                marginBottom: "6px",
                fontSize: "0.88rem",
                fontWeight: 600,
                color: "#334155",
              }}
            >
              Password <span style={{ color: "#ef4444" }}>*</span>{" "}
              <span style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 400 }}>
                (Minimum 8 characters)
              </span>
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="signup-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                disabled={loading}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "11px 44px 11px 14px",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  fontSize: "0.95rem",
                  color: "#0f172a",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#4f46e5")}
                onBlur={(e) => (e.target.style.borderColor = "#cbd5e1")}
              />
              <button
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                style={{
                  position: "absolute",
                  right: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "0.95rem",
                  color: "#64748b",
                  padding: "4px",
                }}
              >
                {showPassword ? "👁️" : "🙈"}
              </button>
            </div>
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label
              htmlFor="signup-confirm-password"
              style={{
                display: "block",
                marginBottom: "6px",
                fontSize: "0.88rem",
                fontWeight: 600,
                color: "#334155",
              }}
            >
              Confirm Password <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <input
              id="signup-confirm-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              disabled={loading}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "11px 14px",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                fontSize: "0.95rem",
                color: "#0f172a",
                outline: "none",
                transition: "border-color 0.2s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#4f46e5")}
              onBlur={(e) => (e.target.style.borderColor = "#cbd5e1")}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: "10px",
              border: "none",
              background: "linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)",
              color: "#ffffff",
              fontSize: "1rem",
              fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.75 : 1,
              boxShadow: "0 4px 10px rgba(79, 70, 229, 0.3)",
              transition: "transform 0.15s, opacity 0.15s",
            }}
          >
            {loading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        {/* Footer Navigation */}
        <div
          style={{
            marginTop: "24px",
            paddingTop: "20px",
            borderTop: "1px solid #f1f5f9",
            textAlign: "center",
            fontSize: "0.9rem",
            color: "#64748b",
          }}
        >
          Already have an account?{" "}
          <Link
            to={`/login?redirect=${encodeURIComponent(redirectTarget)}`}
            style={{
              color: "#4f46e5",
              fontWeight: 700,
              textDecoration: "none",
            }}
          >
            Sign In
          </Link>
          <div style={{ marginTop: "14px" }}>
            <Link
              to="/"
              style={{
                color: "#64748b",
                fontSize: "0.85rem",
                textDecoration: "underline",
              }}
            >
              ← Back to TravelSync Home / Plan as Guest
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
