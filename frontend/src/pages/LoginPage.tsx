import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Compass,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  Info,
  ArrowLeft,
} from "lucide-react";
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
        background: "radial-gradient(ellipse at 50% 0%, var(--accent-bg) 0%, var(--bg) 100%)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "var(--card-bg)",
          borderRadius: "16px",
          boxShadow: "var(--shadow-lg)",
          border: "1px solid var(--border)",
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
            Sign In to Your Account
          </h1>
          <p style={{ margin: 0, fontSize: "0.92rem", color: "var(--text-muted)" }}>
            Access your itineraries, shared trips, and collaborator workspaces
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
            You are currently signed in. Logging in with another email will switch your active session.
          </div>
        )}

        {/* Guest Session Notice */}
        {!alreadyLoggedIn && currentGuestId && (
          <div
            style={{
              marginBottom: "20px",
              padding: "12px 14px",
              background: "var(--code-bg)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
              lineHeight: 1.5,
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
            }}
          >
            <Info size={16} style={{ color: "var(--accent)", flexShrink: 0, marginTop: 2 }} />
            <div>
              <strong>Guest Session Active:</strong> If you planned trips as a guest,{" "}
              <Link
                to={`/signup?claim=true&redirect=${encodeURIComponent(redirectTarget)}`}
                style={{ color: "var(--accent)", fontWeight: 700, textDecoration: "underline" }}
              >
                Sign up here
              </Link>{" "}
              to attach your trips to a new permanent account so they are preserved.
            </div>
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
                color: "var(--input-label)",
              }}
            >
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: "8px",
                border: "1px solid var(--input-border)",
                background: "var(--input-bg)",
                color: "var(--input-text)",
                fontSize: "0.95rem",
                boxSizing: "border-box",
                outline: "none",
                transition: "border-color 0.15s, box-shadow 0.15s",
              }}
            />
          </div>

          <div style={{ marginBottom: "22px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "6px",
              }}
            >
              <label
                htmlFor="login-password"
                style={{
                  fontSize: "0.88rem",
                  fontWeight: 600,
                  color: "var(--input-label)",
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
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: "100%",
                  padding: "11px 40px 11px 14px",
                  borderRadius: "8px",
                  border: "1px solid var(--input-border)",
                  background: "var(--input-bg)",
                  color: "var(--input-text)",
                  fontSize: "0.95rem",
                  boxSizing: "border-box",
                  outline: "none",
                  transition: "border-color 0.15s, box-shadow 0.15s",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
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
            borderTop: "1px solid var(--border)",
            textAlign: "center",
            fontSize: "0.9rem",
            color: "var(--text-muted)",
          }}
        >
          Don't have an account?{" "}
          <Link
            to={`/signup?redirect=${encodeURIComponent(redirectTarget)}`}
            style={{
              color: "var(--accent)",
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
