import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiLogin, getOrCreateUserId, isAuthenticated } from "../services/identity";

interface LoginPageProps {
  onAuthSuccess?: () => void;
}

export default function LoginPage({ onAuthSuccess }: LoginPageProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTarget = searchParams.get("redirect") || "/trip-history";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const currentGuestId = getOrCreateUserId();
  const alreadyLoggedIn = isAuthenticated();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setErrorMessage("Please enter your password.");
      return;
    }

    setLoading(true);

    try {
      const response = await apiLogin(cleanEmail, password);
      setSuccessMessage(`Welcome back, ${response.user?.full_name || response.user?.email}!`);
      
      onAuthSuccess?.();

      setTimeout(() => {
        navigate(redirectTarget);
      }, 600);
    } catch (err: any) {
      console.error("Login failure:", err);
      if (err?.message?.includes("401") || err?.message?.toLowerCase().includes("invalid credentials")) {
        setErrorMessage("Invalid email or password. Please verify your credentials and try again.");
      } else if (err?.message?.includes("429")) {
        setErrorMessage("Too many login attempts. Please wait a moment before trying again.");
      } else {
        setErrorMessage(err?.message || "Sign in failed. Please check your network connection.");
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
        padding: "24px 16px",
        background: "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 100%)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "#ffffff",
          borderRadius: "16px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
          border: "1px solid #e2e8f0",
          padding: "36px 32px",
          boxSizing: "border-box",
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
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
            Sign In to Your Account
          </h1>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b" }}>
            Access your itineraries, shared trips, and collaborator workspaces
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
            You are currently signed in. Logging in with another email will switch your active session.
          </div>
        )}

        {/* Guest Session Notice */}
        {!alreadyLoggedIn && currentGuestId && (
          <div
            style={{
              marginBottom: "20px",
              padding: "12px 14px",
              background: "#f0f9ff",
              border: "1px solid #bae6fd",
              borderRadius: "10px",
              color: "#0369a1",
              fontSize: "0.85rem",
              lineHeight: 1.5,
            }}
          >
            💡 <strong>Guest Session Active:</strong> If you planned trips as a guest,{" "}
            <Link
              to={`/signup?claim=true&redirect=${encodeURIComponent(redirectTarget)}`}
              style={{ color: "#0284c7", fontWeight: 700, textDecoration: "underline" }}
            >
              Sign up here
            </Link>{" "}
            to attach your trips to a new permanent account so they are preserved.
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

        {/* Form */}
        <form onSubmit={handleLogin} noValidate>
          <div style={{ marginBottom: "18px" }}>
            <label
              htmlFor="login-email"
              style={{
                display: "block",
                marginBottom: "6px",
                fontSize: "0.88rem",
                fontWeight: 600,
                color: "#334155",
              }}
            >
              Email Address
            </label>
            <input
              id="login-email"
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
                transition: "border-color 0.2s, box-shadow 0.2s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#4f46e5")}
              onBlur={(e) => (e.target.style.borderColor = "#cbd5e1")}
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label
                htmlFor="login-password"
                style={{
                  fontSize: "0.88rem",
                  fontWeight: 600,
                  color: "#334155",
                }}
              >
                Password
              </label>
            </div>
            <div style={{ position: "relative" }}>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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
            {loading ? "Signing in..." : "Sign In"}
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
          Don't have an account?{" "}
          <Link
            to={`/signup?redirect=${encodeURIComponent(redirectTarget)}`}
            style={{
              color: "#4f46e5",
              fontWeight: 700,
              textDecoration: "none",
            }}
          >
            Create account
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
