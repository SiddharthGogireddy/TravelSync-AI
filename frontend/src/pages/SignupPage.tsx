import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Compass,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  ArrowLeft,
} from "lucide-react";
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
        background: "radial-gradient(ellipse at 50% 0%, var(--accent-bg) 0%, var(--bg) 100%)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "480px",
          background: "var(--card-bg)",
          borderRadius: "16px",
          boxShadow: "var(--shadow-lg)",
          border: "1px solid var(--border)",
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
              color: "var(--accent)",
              fontWeight: 800,
              fontSize: "1.35rem",
              letterSpacing: "-0.02em",
            }}
          >
            <Compass size={24} style={{ color: "var(--accent)" }} />
            <span>TravelSync AI</span>
          </Link>
          <h1
            style={{
              margin: "16px 0 6px 0",
              fontSize: "1.6rem",
              fontWeight: 700,
              color: "var(--text-h)",
            }}
          >
            Create Your Account
          </h1>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)" }}>
            Start planning smart AI itineraries and collaborate with your travel group
          </p>
        </div>

        {alreadyLoggedIn && (
          <div
            style={{
              marginBottom: "20px",
              padding: "12px 14px",
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.25)",
              borderRadius: "10px",
              color: "#10b981",
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
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              borderRadius: "10px",
              color: "#ef4444",
              fontSize: "0.88rem",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <AlertTriangle size={16} style={{ flexShrink: 0 }} />
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
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.25)",
              borderRadius: "10px",
              color: "#10b981",
              fontSize: "0.88rem",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <CheckCircle size={16} style={{ flexShrink: 0 }} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Guest Session Preserving Card */}
        {hasGuestSession && (
          <div
            style={{
              marginBottom: "22px",
              padding: "14px",
              background: "var(--code-bg)",
              border: "1px solid var(--border)",
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
                  accentColor: "var(--accent)",
                  cursor: "pointer",
                }}
              />
              <div>
                <strong style={{ display: "block", color: "var(--text-h)", fontSize: "0.9rem" }}>
                  Preserve and link my existing guest trips
                </strong>
                <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                  Active guest session: <code style={{ color: "var(--text-secondary)" }}>{currentGuestId.slice(0, 18)}...</code>.
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
                color: "var(--input-label)",
              }}
            >
              Full Name <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(Optional)</span>
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
                border: "1px solid var(--input-border)",
                background: "var(--input-bg)",
                color: "var(--input-text)",
                fontSize: "0.95rem",
                outline: "none",
                transition: "border-color 0.2s",
              }}
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
                color: "var(--input-label)",
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
                border: "1px solid var(--input-border)",
                background: "var(--input-bg)",
                color: "var(--input-text)",
                fontSize: "0.95rem",
                outline: "none",
                transition: "border-color 0.2s",
              }}
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
                color: "var(--input-label)",
              }}
            >
              Password <span style={{ color: "#ef4444" }}>*</span>{" "}
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 400 }}>
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
                  border: "1px solid var(--input-border)",
                  background: "var(--input-bg)",
                  color: "var(--input-text)",
                  fontSize: "0.95rem",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
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
                  color: "var(--text-muted)",
                  padding: "4px",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
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
                color: "var(--input-label)",
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
                border: "1px solid var(--input-border)",
                background: "var(--input-bg)",
                color: "var(--input-text)",
                fontSize: "0.95rem",
                outline: "none",
                transition: "border-color 0.2s",
              }}
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
            borderTop: "1px solid var(--border)",
            textAlign: "center",
            fontSize: "0.9rem",
            color: "var(--text-muted)",
          }}
        >
          Already have an account?{" "}
          <Link
            to={`/login?redirect=${encodeURIComponent(redirectTarget)}`}
            style={{
              color: "var(--accent)",
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
                color: "var(--text-muted)",
                fontSize: "0.85rem",
                textDecoration: "underline",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                justifyContent: "center",
              }}
            >
              <ArrowLeft size={14} />
              <span>Back to TravelSync Home / Plan as Guest</span>
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
