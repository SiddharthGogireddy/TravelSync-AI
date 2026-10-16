import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Compass, Edit3, Eye, AlertTriangle, CheckCircle2 } from "lucide-react";
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
          backgroundColor: "var(--card-bg)",
          borderRadius: "16px",
          padding: "32px",
          boxShadow: "var(--card-shadow, 0 10px 25px -5px rgba(0,0,0,0.08))",
          border: "1px solid var(--border)",
          textAlign: "center",
        }}
      >
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
          <Compass size={44} color="var(--accent)" />
        </div>

        <h1 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-h)", margin: "0 0 8px 0" }}>
          Trip Collaboration Invitation
        </h1>

        {loading ? (
          <div style={{ padding: "32px 0", color: "var(--text-muted)" }}>Loading invitation details...</div>
        ) : error ? (
          <div style={{ marginTop: "20px" }}>
            <div
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                color: "#ef4444",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                padding: "14px",
                borderRadius: "10px",
                fontSize: "0.9rem",
                marginBottom: "20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
            >
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
            <button
              onClick={() => navigate("/")}
              style={{
                padding: "10px 20px",
                backgroundColor: "var(--accent)",
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
                  backgroundColor: "rgba(245, 158, 11, 0.1)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  color: "#f59e0b",
                  padding: "14px",
                  borderRadius: "10px",
                  fontSize: "0.9rem",
                  margin: "16px 0",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
              >
                <AlertTriangle size={18} />
                <span>This invitation is <strong>{preview.status.toUpperCase()}</strong> and is no longer active.</span>
              </div>
            ) : (
              <div
                style={{
                  backgroundColor: "var(--bg-alt)",
                  border: "1px solid var(--border)",
                  borderRadius: "12px",
                  padding: "18px",
                  margin: "20px 0",
                  textAlign: "left",
                }}
              >
                <div style={{ marginBottom: "10px" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Destination
                  </span>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-h)" }}>
                    {preview.destination}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                      Duration
                    </span>
                    <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text)" }}>
                      {preview.days} {preview.days === 1 ? "Day" : "Days"}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                      Your Role
                    </span>
                    <div style={{ fontSize: "0.95rem", fontWeight: 700, color: preview.role === "editor" ? "var(--accent)" : "#10b981", display: "flex", alignItems: "center", gap: 5 }}>
                      {preview.role === "editor" ? <Edit3 size={14} /> : <Eye size={14} />}
                      {preview.role === "editor" ? "Editor (Can edit)" : "Viewer (Read only)"}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", borderTop: "1px solid var(--border)", paddingTop: "8px" }}>
                  Expires: {new Date(preview.expires_at).toLocaleDateString()}
                </div>
              </div>
            )}

            {actionStatus && (
              <div
                style={{
                  padding: "12px",
                  backgroundColor: "rgba(16, 185, 129, 0.1)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  color: "#10b981",
                  borderRadius: "8px",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
              >
                <CheckCircle2 size={18} />
                <span>{actionStatus}</span>
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
                    backgroundColor: "var(--bg-alt)",
                    color: "var(--text)",
                    border: "1px solid var(--border)",
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
                  backgroundColor: "var(--accent)",
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
