import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  API,
  previewInvitation,
  acceptInvitation,
  declineInvitation,
} from "../services/api";
import { ensureAuthSession } from "../services/identity";
import type { InvitationPreview } from "../services/api";

export default function InvitationAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("No invitation token provided");
      setLoading(false);
      return;
    }

    previewInvitation(token)
      .then((data) => {
        setPreview(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load invitation preview");
        setLoading(false);
      });
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    try {
      setActionLoading(true);
      await ensureAuthSession(API);
      const res = await acceptInvitation(token);
      setActionStatus("Invitation accepted! Redirecting to trip...");
      setTimeout(() => {
        navigate(`/trip/${res.trip_id}`);
      }, 1200);
    } catch (err: any) {
      alert(err.message || "Failed to accept invitation");
      setActionLoading(false);
    }
  };

  const handleDecline = async () => {
    if (!token) return;
    if (!window.confirm("Are you sure you want to decline this trip invitation?")) return;
    try {
      setActionLoading(true);
      await ensureAuthSession(API);
      await declineInvitation(token);
      setActionStatus("Invitation declined.");
      setTimeout(() => {
        navigate("/");
      }, 1200);
    } catch (err: any) {
      alert(err.message || "Failed to decline invitation");
      setActionLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "75vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "480px",
          backgroundColor: "#ffffff",
          borderRadius: "16px",
          padding: "32px",
          boxShadow: "0 10px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04)",
          border: "1px solid #e2e8f0",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "2.5rem", marginBottom: "12px" }}>✈️</div>

        <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#0f172a", margin: "0 0 8px 0" }}>
          Trip Collaboration Invitation
        </h1>

        {loading ? (
          <div style={{ padding: "32px 0", color: "#64748b" }}>Loading invitation details...</div>
        ) : error ? (
          <div style={{ marginTop: "20px" }}>
            <div
              style={{
                backgroundColor: "#fee2e2",
                color: "#991b1b",
                padding: "14px",
                borderRadius: "10px",
                fontSize: "0.9rem",
                marginBottom: "20px",
              }}
            >
              {error}
            </div>
            <button
              onClick={() => navigate("/")}
              style={{
                padding: "10px 20px",
                backgroundColor: "#4f46e5",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Return to Home
            </button>
          </div>
        ) : preview ? (
          <div>
            {!preview.valid ? (
              <div
                style={{
                  backgroundColor: "#fef3c7",
                  color: "#92400e",
                  padding: "14px",
                  borderRadius: "10px",
                  fontSize: "0.9rem",
                  margin: "16px 0",
                }}
              >
                This invitation is <strong>{preview.status.toUpperCase()}</strong> and is no longer active.
              </div>
            ) : (
              <div
                style={{
                  backgroundColor: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "12px",
                  padding: "18px",
                  margin: "20px 0",
                  textAlign: "left",
                }}
              >
                <div style={{ marginBottom: "10px" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>
                    Destination
                  </span>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
                    {preview.destination}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>
                      Duration
                    </span>
                    <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#334155" }}>
                      {preview.days} {preview.days === 1 ? "Day" : "Days"}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>
                      Your Role
                    </span>
                    <div style={{ fontSize: "0.95rem", fontWeight: 700, color: preview.role === "editor" ? "#2563eb" : "#059669" }}>
                      {preview.role === "editor" ? "✏️ Editor (Can edit)" : "👁️ Viewer (Read only)"}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: "0.75rem", color: "#64748b", borderTop: "1px solid #e2e8f0", paddingTop: "8px" }}>
                  Expires: {new Date(preview.expires_at).toLocaleDateString()}
                </div>
              </div>
            )}

            {actionStatus && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "#ecfdf5",
                  color: "#065f46",
                  borderRadius: "8px",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  marginBottom: "16px",
                }}
              >
                {actionStatus}
              </div>
            )}

            {preview.valid && !actionStatus && (
              <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
                <button
                  onClick={handleAccept}
                  disabled={actionLoading}
                  style={{
                    flex: 1,
                    padding: "12px",
                    backgroundColor: "#16a34a",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    fontWeight: 700,
                    fontSize: "0.95rem",
                    cursor: actionLoading ? "not-allowed" : "pointer",
                    opacity: actionLoading ? 0.7 : 1,
                  }}
                >
                  {actionLoading ? "Accepting..." : "Accept Invitation"}
                </button>
                <button
                  onClick={handleDecline}
                  disabled={actionLoading}
                  style={{
                    padding: "12px 18px",
                    backgroundColor: "#f1f5f9",
                    color: "#64748b",
                    border: "1px solid #cbd5e1",
                    borderRadius: "8px",
                    fontWeight: 600,
                    fontSize: "0.95rem",
                    cursor: actionLoading ? "not-allowed" : "pointer",
                  }}
                >
                  Decline
                </button>
              </div>
            )}

            {!preview.valid && (
              <button
                onClick={() => navigate("/")}
                style={{
                  padding: "10px 20px",
                  backgroundColor: "#4f46e5",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Return to Home
              </button>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
