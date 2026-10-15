import React, { useState } from "react";
import {
  apiLogin,
  apiRegister,
  apiClaimSession,
  getOrCreateUserId,
} from "../services/identity";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  apiBase?: string;
}

export default function AuthModal({ isOpen, onClose, onSuccess, apiBase }: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register" | "claim">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentGuestId = getOrCreateUserId();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setLoading(true);

    try {
      if (mode === "login") {
        await apiLogin(email, password, apiBase);
        setSuccessMessage("Logged in successfully!");
      } else if (mode === "register") {
        await apiRegister(email, password, fullName || undefined, apiBase);
        setSuccessMessage("Account created successfully!");
      } else if (mode === "claim") {
        await apiClaimSession(email, password, fullName || undefined, apiBase);
        setSuccessMessage("Session claimed! All your existing trips are now saved to your account.");
      }

      setTimeout(() => {
        onSuccess?.();
        onClose();
      }, 700);
    } catch (err: any) {
      setError(err?.message || "Authentication failed. Please verify your details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: "#ffffff",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "440px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
          overflow: "hidden",
          border: "1px solid #e2e8f0",
        }}
      >
        {/* Header Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid #e2e8f0", background: "#f8fafc" }}>
          <button
            type="button"
            onClick={() => { setMode("login"); setError(null); }}
            style={{
              flex: 1,
              padding: "14px 12px",
              fontWeight: 600,
              fontSize: "0.95rem",
              border: "none",
              borderBottom: mode === "login" ? "2px solid #4f46e5" : "2px solid transparent",
              background: mode === "login" ? "#ffffff" : "transparent",
              color: mode === "login" ? "#4f46e5" : "#64748b",
              cursor: "pointer",
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setError(null); }}
            style={{
              flex: 1,
              padding: "14px 12px",
              fontWeight: 600,
              fontSize: "0.95rem",
              border: "none",
              borderBottom: mode === "register" ? "2px solid #4f46e5" : "2px solid transparent",
              background: mode === "register" ? "#ffffff" : "transparent",
              color: mode === "register" ? "#4f46e5" : "#64748b",
              cursor: "pointer",
            }}
          >
            Create Account
          </button>
          <button
            type="button"
            onClick={() => { setMode("claim"); setError(null); }}
            style={{
              flex: 1,
              padding: "14px 12px",
              fontWeight: 600,
              fontSize: "0.95rem",
              border: "none",
              borderBottom: mode === "claim" ? "2px solid #4f46e5" : "2px solid transparent",
              background: mode === "claim" ? "#ffffff" : "transparent",
              color: mode === "claim" ? "#4f46e5" : "#64748b",
              cursor: "pointer",
            }}
          >
            Save Session
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: "24px" }}>
          <div style={{ marginBottom: "16px" }}>
            <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#0f172a", fontWeight: 700 }}>
              {mode === "login" && "Sign In to TravelSync"}
              {mode === "register" && "Create New Account"}
              {mode === "claim" && "Save Your Guest Session"}
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: "0.875rem", color: "#64748b" }}>
              {mode === "login" && "Access your synchronized trips and collaborator workspaces."}
              {mode === "register" && "Start planning, sharing, and collaborating on travel itineraries."}
              {mode === "claim" && `Attach credentials to ${currentGuestId} so you keep all current trips.`}
            </p>
          </div>

          {error && (
            <div
              style={{
                marginBottom: "16px",
                padding: "10px 14px",
                backgroundColor: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "8px",
                color: "#b91c1c",
                fontSize: "0.875rem",
              }}
            >
              {error}
            </div>
          )}

          {successMessage && (
            <div
              style={{
                marginBottom: "16px",
                padding: "10px 14px",
                backgroundColor: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "8px",
                color: "#15803d",
                fontSize: "0.875rem",
              }}
            >
              {successMessage}
            </div>
          )}

          {(mode === "register" || mode === "claim") && (
            <div style={{ marginBottom: "14px" }}>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "#334155", marginBottom: "6px" }}>
                Full Name (Optional)
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Alex Morgan"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  border: "1px solid #cbd5e1",
                  fontSize: "0.95rem",
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "#334155", marginBottom: "6px" }}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                fontSize: "0.95rem",
              }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "#334155", marginBottom: "6px" }}>
              Password
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                fontSize: "0.95rem",
              }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: "10px 16px",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                backgroundColor: "#ffffff",
                color: "#475569",
                fontWeight: 600,
                fontSize: "0.9rem",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "10px 20px",
                borderRadius: "8px",
                border: "none",
                backgroundColor: "#4f46e5",
                color: "#ffffff",
                fontWeight: 600,
                fontSize: "0.9rem",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? "Processing..." : mode === "login" ? "Sign In" : mode === "register" ? "Create Account" : "Save Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
