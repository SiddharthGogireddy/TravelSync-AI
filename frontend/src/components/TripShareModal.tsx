import { useState, useEffect } from "react";
import {
  createTripInvitation,
  getTripInvitations,
  revokeTripInvitation,
} from "../services/api";
import type { TripInvitation } from "../services/api";

interface TripShareModalProps {
  tripId: string;
  isOpen: boolean;
  onClose: () => void;
  userRole?: "owner" | "editor" | "viewer";
}

export default function TripShareModal({
  tripId,
  isOpen,
  onClose,
  userRole = "owner",
}: TripShareModalProps) {
  const [role, setRole] = useState<"viewer" | "editor">("viewer");
  const [expiryDays, setExpiryDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [createdInvite, setCreatedInvite] = useState<TripInvitation | null>(null);
  const [invitations, setInvitations] = useState<TripInvitation[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && tripId && userRole === "owner") {
      fetchInvitations();
    }
  }, [isOpen, tripId, userRole]);

  const fetchInvitations = async () => {
    try {
      setLoadingList(true);
      const list = await getTripInvitations(tripId);
      setInvitations(list);
    } catch (err: any) {
      console.warn("Could not fetch invitations:", err.message);
    } finally {
      setLoadingList(false);
    }
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);
      setCopySuccess(false);
      const invite = await createTripInvitation(tripId, role, expiryDays);
      setCreatedInvite(invite);
      await fetchInvitations();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to create invitation");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (!createdInvite?.token) return;
    const inviteUrl = `${window.location.origin}/invite/${createdInvite.token}`;
    navigator.clipboard.writeText(inviteUrl);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2500);
  };

  const handleRevoke = async (invitationId: string) => {
    try {
      await revokeTripInvitation(tripId, invitationId);
      if (createdInvite?.invitation_id === invitationId) {
        setCreatedInvite(null);
      }
      await fetchInvitations();
    } catch (err: any) {
      alert(err.message || "Failed to revoke invitation");
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
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
          maxWidth: "560px",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "24px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
          border: "1px solid #e2e8f0",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#0f172a", fontWeight: 700 }}>
            🔗 Share Trip & Manage Invitations
          </h2>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: "1.5rem",
              cursor: "pointer",
              color: "#64748b",
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {userRole !== "owner" ? (
          <div
            style={{
              padding: "16px",
              backgroundColor: "#fef3c7",
              color: "#92400e",
              borderRadius: "8px",
              fontSize: "0.9rem",
            }}
          >
            Only the trip owner can create and manage collaborator invitations. You are currently a{" "}
            <strong>{userRole}</strong> on this trip.
          </div>
        ) : (
          <>
            <p style={{ color: "#475569", fontSize: "0.875rem", marginTop: 0, marginBottom: "20px" }}>
              Invite travel companions with cryptographically secure links. All trips are private by default.
            </p>

            {errorMessage && (
              <div
                style={{
                  padding: "10px 14px",
                  backgroundColor: "#fee2e2",
                  color: "#991b1b",
                  borderRadius: "8px",
                  fontSize: "0.85rem",
                  marginBottom: "16px",
                }}
              >
                {errorMessage}
              </div>
            )}

            {/* Invitation Form */}
            <div
              style={{
                backgroundColor: "#f8fafc",
                padding: "16px",
                borderRadius: "12px",
                border: "1px solid #e2e8f0",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#334155", marginBottom: "6px" }}>
                    Access Level
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as "viewer" | "editor")}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      backgroundColor: "#fff",
                      color: "#0f172a",
                      fontSize: "0.875rem",
                    }}
                  >
                    <option value="viewer">👁️ Viewer (Read Only)</option>
                    <option value="editor">✏️ Editor (Can Edit Itinerary)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#334155", marginBottom: "6px" }}>
                    Expires In
                  </label>
                  <select
                    value={expiryDays}
                    onChange={(e) => setExpiryDays(Number(e.target.value))}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      backgroundColor: "#fff",
                      color: "#0f172a",
                      fontSize: "0.875rem",
                    }}
                  >
                    <option value={1}>1 Day</option>
                    <option value={7}>7 Days (Default)</option>
                    <option value={14}>14 Days</option>
                    <option value={30}>30 Days</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleCreate}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "10px",
                  backgroundColor: "#4f46e5",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  fontWeight: 600,
                  fontSize: "0.875rem",
                  cursor: loading ? "not-allowed" : "pointer",
                  opacity: loading ? 0.7 : 1,
                  transition: "background-color 0.2s",
                }}
              >
                {loading ? "Generating Link..." : "Generate Secure Invite Link"}
              </button>
            </div>

            {/* Generated Link Display */}
            {createdInvite?.token && (
              <div
                style={{
                  backgroundColor: "#ecfdf5",
                  border: "1px solid #a7f3d0",
                  borderRadius: "12px",
                  padding: "14px",
                  marginBottom: "20px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "#065f46" }}>
                    ✓ Invite Link Ready ({createdInvite.role.toUpperCase()})
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "#047857" }}>
                    Expires: {new Date(createdInvite.expires_at).toLocaleDateString()}
                  </span>
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="text"
                    readOnly
                    value={`${window.location.origin}/invite/${createdInvite.token}`}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      fontSize: "0.8rem",
                      backgroundColor: "#fff",
                      border: "1px solid #a7f3d0",
                      borderRadius: "6px",
                      color: "#0f172a",
                    }}
                  />
                  <button
                    onClick={handleCopyLink}
                    style={{
                      padding: "8px 14px",
                      backgroundColor: copySuccess ? "#059669" : "#10b981",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      fontWeight: 600,
                      fontSize: "0.8rem",
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {copySuccess ? "Copied! ✓" : "Copy Link"}
                  </button>
                </div>
              </div>
            )}

            {/* Invitation History */}
            <div>
              <h3 style={{ fontSize: "0.95rem", color: "#1e293b", margin: "0 0 10px 0" }}>
                Active & Past Invitations
              </h3>
              {loadingList ? (
                <div style={{ fontSize: "0.85rem", color: "#64748b", padding: "8px 0" }}>Loading invitations...</div>
              ) : invitations.length === 0 ? (
                <div style={{ fontSize: "0.85rem", color: "#94a3b8", fontStyle: "italic", padding: "8px 0" }}>
                  No invitations generated yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {invitations.map((inv) => (
                    <div
                      key={inv.invitation_id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 14px",
                        backgroundColor: "#f8fafc",
                        borderRadius: "8px",
                        border: "1px solid #e2e8f0",
                        fontSize: "0.8rem",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: "#1e293b" }}>
                          {inv.role === "editor" ? "✏️ Editor" : "👁️ Viewer"} —{" "}
                          <span
                            style={{
                              color:
                                inv.status === "pending"
                                  ? "#d97706"
                                  : inv.status === "accepted"
                                  ? "#16a34a"
                                  : inv.status === "revoked"
                                  ? "#dc2626"
                                  : "#64748b",
                              textTransform: "capitalize",
                            }}
                          >
                            {inv.status}
                          </span>
                        </div>
                        <div style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "2px" }}>
                          Expires: {new Date(inv.expires_at).toLocaleDateString()}
                          {inv.accepted_by && ` • Accepted`}
                        </div>
                      </div>

                      {inv.status === "pending" && (
                        <button
                          onClick={() => handleRevoke(inv.invitation_id)}
                          style={{
                            padding: "4px 10px",
                            backgroundColor: "#fee2e2",
                            color: "#b91c1c",
                            border: "1px solid #fca5a5",
                            borderRadius: "6px",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
