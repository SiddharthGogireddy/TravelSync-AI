import React, { useState, useEffect } from "react";
import { MessageSquare, X, Loader2, AlertTriangle, MapPin } from "lucide-react";
import {
  getAttractionComments,
  addAttractionComment,
  editTripChatMessage,
  deleteTripChatMessage,
} from "../services/api";
import type { ChatMessage } from "../services/api";
import { getCurrentUserId } from "../services/identity";

interface AttractionCommentsModalProps {
  isOpen: boolean;
  onClose: () => void;
  tripId: string;
  attractionName: string;
  attractionCategory?: string;
  userRole?: string;
}

export default function AttractionCommentsModal({
  isOpen,
  onClose,
  tripId,
  attractionName,
  attractionCategory,
  userRole = "viewer",
}: AttractionCommentsModalProps) {
  const currentUserId = getCurrentUserId();
  const [comments, setComments] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [draftContent, setDraftContent] = useState<string>("");
  const [sending, setSending] = useState<boolean>(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>("");
  const [savingEdit, setSavingEdit] = useState<boolean>(false);
  const [editError, setEditError] = useState<string | null>(null);

  const isOwner = userRole === "owner";

  const loadComments = async () => {
    if (!tripId || !attractionName) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getAttractionComments(tripId, attractionName);
      setComments(res.messages || []);
    } catch (err: any) {
      setError(err.message || "Failed to load attraction comments");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && tripId && attractionName) {
      loadComments();
      setDraftContent("");
      setSendError(null);
      setEditingId(null);
    }
  }, [isOpen, tripId, attractionName]);

  if (!isOpen) return null;

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = draftContent.trim();
    if (!clean || sending) return;

    if (clean.length > 2000) {
      setSendError("Comment exceeds maximum length of 2000 characters.");
      return;
    }

    setSending(true);
    setSendError(null);

    try {
      const newComment = await addAttractionComment(tripId, attractionName, clean);
      setComments((prev) => [...prev, newComment]);
      setDraftContent("");
    } catch (err: any) {
      // PRESERVE user's draft on failure!
      setSendError(err.message || "Failed to post comment. Your draft has been preserved.");
    } finally {
      setSending(false);
    }
  };

  const handleStartEdit = (msg: ChatMessage) => {
    setEditingId(msg.id);
    setEditContent(msg.content);
    setEditError(null);
  };

  const handleSaveEdit = async (messageId: string) => {
    const clean = editContent.trim();
    if (!clean) {
      setEditError("Comment content cannot be blank.");
      return;
    }
    setSavingEdit(true);
    setEditError(null);

    try {
      const updated = await editTripChatMessage(tripId, messageId, clean);
      setComments((prev) => prev.map((c) => (c.id === messageId ? updated : c)));
      setEditingId(null);
      setEditContent("");
    } catch (err: any) {
      setEditError(err.message || "Failed to update comment.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteComment = async (messageId: string) => {
    if (!window.confirm("Delete this comment?")) return;
    try {
      await deleteTripChatMessage(tripId, messageId);
      setComments((prev) => prev.filter((c) => c.id !== messageId));
    } catch (err: any) {
      alert(err.message || "Failed to delete comment.");
    }
  };

  const formatTimestamp = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) +
        " · " +
        d.toLocaleDateString([], { month: "short", day: "numeric" });
    } catch {
      return isoStr;
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--card-bg)",
          borderRadius: 16,
          width: "100%",
          maxWidth: 580,
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "var(--shadow-lg)",
          border: "1px solid var(--border)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "var(--code-bg)",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <MessageSquare size={18} style={{ color: "var(--accent)" }} />
              <h3 style={{ margin: 0, fontSize: "1.15rem", color: "var(--text-h)" }}>
                {attractionName}
              </h3>
            </div>
            {attractionCategory && (
              <p style={{ margin: "2px 0 0", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                {attractionCategory} • Itinerary Attraction Discussion
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close attraction discussion"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "4px 8px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Comments List Container */}
        <div
          style={{
            padding: "20px 24px",
            overflowY: "auto",
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 12,
            minHeight: 180,
            background: "var(--card-bg)",
          }}
        >
          {loading && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
              <span>Loading discussion...</span>
            </div>
          )}

          {!loading && error && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                borderRadius: 8,
                padding: "12px",
                color: "#ef4444",
                fontSize: "0.85rem",
                textAlign: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <AlertTriangle size={15} />
                <span>{error}</span>
              </div>
              <div style={{ marginTop: 6 }}>
                <button
                  type="button"
                  onClick={loadComments}
                  style={{
                    background: "#ef4444",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    padding: "4px 10px",
                    cursor: "pointer",
                    fontSize: "0.78rem",
                  }}
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {!loading && !error && comments.length === 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "40px 20px",
                color: "var(--text-muted)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>
                <MapPin size={24} style={{ color: "var(--text-muted)" }} />
              </div>
              <div style={{ fontWeight: 600, color: "var(--text-h)" }}>
                No comments on {attractionName} yet
              </div>
              <p style={{ margin: "4px 0 0", fontSize: "0.82rem" }}>
                Leave a suggestion, preferred arrival time, or notes for the group!
              </p>
            </div>
          )}

          {!loading &&
            !error &&
            comments.map((msg) => {
              const isMe = msg.sender_id === currentUserId;
              const canEdit = isMe;
              const canDelete = isMe || isOwner;
              const isEditing = editingId === msg.id;

              return (
                <div
                  key={msg.id}
                  style={{
                    background: isMe ? "#f0f4ff" : "#f8fafc",
                    border: isMe ? "1px solid #c7d2fe" : "1px solid #e2e8f0",
                    borderRadius: 10,
                    padding: "12px 14px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: "0.82rem",
                        color: isMe ? "#3730a3" : "#0f172a",
                      }}
                    >
                      {isMe ? "You" : msg.sender_name || msg.sender_id}
                    </span>
                    <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                      {formatTimestamp(msg.created_at)}
                    </span>
                  </div>

                  {isEditing ? (
                    <div style={{ marginTop: 6 }}>
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        rows={2}
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          borderRadius: 6,
                          border: "1px solid #818cf8",
                          fontSize: "0.86rem",
                        }}
                      />
                      {editError && (
                        <div style={{ color: "#ef4444", fontSize: "0.74rem", marginTop: 2, display: "flex", alignItems: "center", gap: 4 }}>
                          <AlertTriangle size={12} />
                          <span>{editError}</span>
                        </div>
                      )}
                      <div style={{ display: "flex", gap: 6, marginTop: 6, justifyContent: "flex-end" }}>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          style={{
                            padding: "3px 8px",
                            fontSize: "0.75rem",
                            borderRadius: 4,
                            background: "var(--code-bg)",
                            color: "var(--text-secondary)",
                            border: "1px solid var(--border)",
                            cursor: "pointer",
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveEdit(msg.id)}
                          disabled={savingEdit}
                          style={{
                            padding: "3px 10px",
                            fontSize: "0.75rem",
                            borderRadius: 4,
                            background: "var(--accent)",
                            color: "#fff",
                            border: "none",
                            cursor: savingEdit ? "not-allowed" : "pointer",
                          }}
                        >
                          {savingEdit ? "Saving..." : "Save"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div
                        style={{
                          fontSize: "0.88rem",
                          color: "var(--text-h)",
                          lineHeight: 1.45,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {msg.content}
                      </div>

                      {msg.is_edited && (
                        <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                          (edited)
                        </span>
                      )}

                      {(canEdit || canDelete) && (
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            marginTop: 6,
                            justifyContent: "flex-end",
                          }}
                        >
                          {canEdit && (
                            <button
                              type="button"
                              onClick={() => handleStartEdit(msg)}
                              style={{
                                background: "transparent",
                                border: "none",
                                color: "var(--accent)",
                                fontSize: "0.72rem",
                                fontWeight: 600,
                                cursor: "pointer",
                              }}
                            >
                              Edit
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              onClick={() => handleDeleteComment(msg.id)}
                              style={{
                                background: "transparent",
                                border: "none",
                                color: "#ef4444",
                                fontSize: "0.72rem",
                                fontWeight: 600,
                                cursor: "pointer",
                              }}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
        </div>

        {/* Input / Post Box */}
        <form
          onSubmit={handleAddComment}
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--border)",
            background: "var(--code-bg)",
          }}
        >
          {sendError && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                borderRadius: 6,
                padding: "8px 12px",
                color: "#ef4444",
                fontSize: "0.8rem",
                marginBottom: 8,
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <AlertTriangle size={13} />
              <span>{sendError}</span>
            </div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <input
              type="text"
              value={draftContent}
              onChange={(e) => setDraftContent(e.target.value)}
              placeholder={`Add comment for ${attractionName}...`}
              disabled={sending}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 8,
                border: "1px solid var(--input-border)",
                background: "var(--input-bg)",
                color: "var(--input-text)",
                fontSize: "0.88rem",
                outline: "none",
              }}
            />
            <button
              type="submit"
              disabled={sending || !draftContent.trim()}
              style={{
                background:
                  sending || !draftContent.trim()
                    ? "var(--border)"
                    : "var(--accent)",
                color: "#ffffff",
                border: "none",
                borderRadius: 8,
                padding: "10px 18px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: sending || !draftContent.trim() ? "not-allowed" : "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {sending ? "Posting..." : "Post"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
