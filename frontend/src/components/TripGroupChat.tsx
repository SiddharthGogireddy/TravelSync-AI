import React, { useState, useEffect, useRef } from "react";
import {
  getTripChatMessages,
  sendTripChatMessage,
  editTripChatMessage,
  deleteTripChatMessage,
} from "../services/api";
import type { ChatMessage } from "../services/api";
import { getCurrentUserId } from "../services/identity";

interface TripGroupChatProps {
  tripId: string;
  userRole?: string;
  travelerNames?: string[];
}

export default function TripGroupChat({
  tripId,
  userRole = "viewer",
  travelerNames = [],
}: TripGroupChatProps) {
  const currentUserId = getCurrentUserId();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Draft state
  const [draftContent, setDraftContent] = useState<string>("");
  const [sending, setSending] = useState<boolean>(false);
  const [sendError, setSendError] = useState<string | null>(null);

  // Edit state
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>("");
  const [savingEdit, setSavingEdit] = useState<boolean>(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Deleting state
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const isOwner = userRole === "owner";

  const loadMessages = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const res = await getTripChatMessages(tripId, {
        target_type: "trip",
        limit: 100,
      });
      setMessages(res.messages || []);
    } catch (err: any) {
      setError(err.message || "Failed to load chat messages.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (tripId) {
      loadMessages();
    }
  }, [tripId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = draftContent.trim();
    if (!clean || sending) return;

    if (clean.length > 2000) {
      setSendError("Message exceeds maximum length of 2000 characters.");
      return;
    }

    setSending(true);
    setSendError(null);

    try {
      const newMsg = await sendTripChatMessage(tripId, clean, {
        target_type: "trip",
        sender_name: travelerNames?.[0] || undefined,
      });
      // Append new message safely and clear draft ONLY on success
      setMessages((prev) => [...prev, newMsg]);
      setDraftContent("");
      setTimeout(scrollToBottom, 50);
    } catch (err: any) {
      // PRESERVE user's draft on failure!
      setSendError(err.message || "Failed to send message. Your draft has been preserved.");
    } finally {
      setSending(false);
    }
  };

  const handleStartEdit = (msg: ChatMessage) => {
    setEditingMessageId(msg.id);
    setEditContent(msg.content);
    setEditError(null);
  };

  const handleCancelEdit = () => {
    setEditingMessageId(null);
    setEditContent("");
    setEditError(null);
  };

  const handleSaveEdit = async (messageId: string) => {
    const clean = editContent.trim();
    if (!clean) {
      setEditError("Message content cannot be blank.");
      return;
    }
    setSavingEdit(true);
    setEditError(null);

    try {
      const updated = await editTripChatMessage(tripId, messageId, clean);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? updated : m))
      );
      setEditingMessageId(null);
      setEditContent("");
    } catch (err: any) {
      setEditError(err.message || "Failed to update message.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteMessage = async (messageId: string) => {
    if (!window.confirm("Are you sure you want to delete this message?")) return;

    setDeletingId(messageId);
    try {
      await deleteTripChatMessage(tripId, messageId);
      setMessages((prev) => prev.filter((m) => m.id !== messageId));
    } catch (err: any) {
      alert(err.message || "Failed to delete message.");
    } finally {
      setDeletingId(null);
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

  // Deterministic color generation for sender badge
  const getSenderColor = (senderId: string) => {
    let hash = 0;
    for (let i = 0; i < senderId.length; i++) {
      hash = senderId.charCodeAt(i) + ((hash << 5) - hash);
    }
    const colors = [
      "#4f46e5", "#0891b2", "#059669", "#d97706",
      "#dc2626", "#7c3aed", "#2563eb", "#db2777"
    ];
    return colors[Math.abs(hash) % colors.length];
  };

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: 16,
        padding: "24px",
        margin: "24px 0",
        boxShadow: "0 4px 14px rgba(15, 23, 42, 0.05)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          borderBottom: "1px solid #f1f5f9",
          paddingBottom: 16,
          marginBottom: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h3
              style={{
                margin: 0,
                fontSize: "1.25rem",
                color: "#0f172a",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>💬</span> Trip Group Chat
            </h3>
            <span
              style={{
                background: "#f1f5f9",
                color: "#475569",
                padding: "3px 10px",
                borderRadius: 12,
                fontSize: "0.78rem",
                fontWeight: 600,
              }}
            >
              {messages.length} message{messages.length === 1 ? "" : "s"}
            </span>
          </div>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "0.85rem" }}>
            Collaborate, plan meetups, and share trip notes with your fellow travelers.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            type="button"
            onClick={() => loadMessages(true)}
            disabled={refreshing || loading}
            style={{
              background: "#f8fafc",
              border: "1px solid #cbd5e1",
              color: "#334155",
              borderRadius: 8,
              padding: "6px 14px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: refreshing || loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.15s ease",
            }}
          >
            <span style={{ display: "inline-block", transform: refreshing ? "rotate(180deg)" : "none", transition: "transform 0.3s" }}>
              🔄
            </span>
            {refreshing ? "Refreshing..." : "Refresh Chat"}
          </button>
        </div>
      </div>

      {/* Info Notice regarding message synchronization */}
      <div
        style={{
          background: "#f8fafc",
          border: "1px dashed #cbd5e1",
          borderRadius: 8,
          padding: "8px 14px",
          marginBottom: 16,
          fontSize: "0.78rem",
          color: "#64748b",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 6,
        }}
      >
        <span>
          ℹ️ <strong>Sync mode:</strong> Messages update when sending or clicking "Refresh Chat".
        </span>
        <span style={{ color: "#94a3b8" }}>
          Signed in as: <strong style={{ color: "#334155" }}>{currentUserId}</strong>
        </span>
      </div>

      {/* Message List Box */}
      <div
        style={{
          minHeight: 220,
          maxHeight: 460,
          overflowY: "auto",
          background: "#fcfdfe",
          border: "1px solid #e2e8f0",
          borderRadius: 12,
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        {loading && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>
            <div style={{ fontSize: "1.4rem", marginBottom: 8 }}>⏳</div>
            <p style={{ margin: 0, fontSize: "0.9rem" }}>Loading group discussion...</p>
          </div>
        )}

        {!loading && error && (
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 8,
              padding: "14px",
              textAlign: "center",
              color: "#991b1b",
              fontSize: "0.88rem",
            }}
          >
            <p style={{ margin: "0 0 8px" }}>⚠️ {error}</p>
            <button
              type="button"
              onClick={() => loadMessages()}
              style={{
                background: "#dc2626",
                color: "#ffffff",
                border: "none",
                padding: "6px 14px",
                borderRadius: 6,
                fontWeight: 600,
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "50px 20px",
              color: "#64748b",
            }}
          >
            <div style={{ fontSize: "2rem", marginBottom: 8 }}>💬</div>
            <div style={{ fontWeight: 600, color: "#334155", fontSize: "0.95rem" }}>
              No messages in this trip yet
            </div>
            <p style={{ margin: "4px 0 0", fontSize: "0.84rem" }}>
              Say hello or discuss your travel plans with the group below!
            </p>
          </div>
        )}

        {!loading &&
          !error &&
          messages.map((msg) => {
            const isMe = msg.sender_id === currentUserId;
            const canEdit = isMe;
            const canDelete = isMe || isOwner;
            const avatarColor = getSenderColor(msg.sender_id);
            const isEditing = editingMessageId === msg.id;

            return (
              <div
                key={msg.id}
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "flex-start",
                  alignSelf: isMe ? "flex-end" : "flex-start",
                  maxWidth: "85%",
                }}
              >
                {!isMe && (
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: "50%",
                      background: avatarColor,
                      color: "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.82rem",
                      fontWeight: 700,
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                    title={msg.sender_id}
                  >
                    {(msg.sender_name || msg.sender_id).substring(0, 2).toUpperCase()}
                  </div>
                )}

                <div
                  style={{
                    background: isMe ? "#f0f4ff" : "#ffffff",
                    border: isMe ? "1px solid #c7d2fe" : "1px solid #e2e8f0",
                    borderRadius: 12,
                    padding: "12px 16px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                    minWidth: 180,
                  }}
                >
                  {/* Sender & Timestamp Header */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 10,
                      marginBottom: 6,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: "0.82rem",
                          color: isMe ? "#3730a3" : "#1e293b",
                        }}
                      >
                        {isMe ? "You" : msg.sender_name || msg.sender_id}
                      </span>
                      {isMe && (
                        <span
                          style={{
                            background: "#e0e7ff",
                            color: "#4338ca",
                            fontSize: "0.68rem",
                            padding: "1px 6px",
                            borderRadius: 8,
                            fontWeight: 600,
                          }}
                        >
                          Owner / Author
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                      {formatTimestamp(msg.created_at)}
                    </span>
                  </div>

                  {/* Message Body or Inline Edit */}
                  {isEditing ? (
                    <div style={{ marginTop: 8 }}>
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        rows={3}
                        style={{
                          width: "100%",
                          padding: "8px 10px",
                          borderRadius: 8,
                          border: "1px solid #818cf8",
                          fontSize: "0.88rem",
                          fontFamily: "inherit",
                          resize: "vertical",
                        }}
                      />
                      {editError && (
                        <div style={{ color: "#dc2626", fontSize: "0.76rem", marginTop: 4 }}>
                          ⚠️ {editError}
                        </div>
                      )}
                      <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
                        <button
                          type="button"
                          onClick={handleCancelEdit}
                          disabled={savingEdit}
                          style={{
                            background: "#f1f5f9",
                            border: "none",
                            padding: "4px 10px",
                            borderRadius: 6,
                            fontSize: "0.78rem",
                            fontWeight: 600,
                            cursor: "pointer",
                            color: "#475569",
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveEdit(msg.id)}
                          disabled={savingEdit}
                          style={{
                            background: "#4f46e5",
                            color: "#ffffff",
                            border: "none",
                            padding: "4px 12px",
                            borderRadius: 6,
                            fontSize: "0.78rem",
                            fontWeight: 600,
                            cursor: savingEdit ? "not-allowed" : "pointer",
                          }}
                        >
                          {savingEdit ? "Saving..." : "Save"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div
                        style={{
                          fontSize: "0.9rem",
                          color: "#1e293b",
                          lineHeight: 1.5,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {msg.content}
                      </div>

                      {msg.is_edited && (
                        <span
                          style={{
                            fontSize: "0.7rem",
                            color: "#94a3b8",
                            fontStyle: "italic",
                            display: "inline-block",
                            marginTop: 4,
                          }}
                        >
                          (edited)
                        </span>
                      )}

                      {/* Actions row */}
                      {(canEdit || canDelete) && (
                        <div
                          style={{
                            display: "flex",
                            gap: 10,
                            marginTop: 8,
                            paddingTop: 6,
                            borderTop: "1px dashed #e2e8f0",
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
                                color: "#4f46e5",
                                fontSize: "0.74rem",
                                fontWeight: 600,
                                cursor: "pointer",
                                padding: 0,
                              }}
                            >
                              Edit
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              onClick={() => handleDeleteMessage(msg.id)}
                              disabled={deletingId === msg.id}
                              style={{
                                background: "transparent",
                                border: "none",
                                color: "#dc2626",
                                fontSize: "0.74rem",
                                fontWeight: 600,
                                cursor: deletingId === msg.id ? "not-allowed" : "pointer",
                                padding: 0,
                              }}
                            >
                              {deletingId === msg.id
                                ? "Deleting..."
                                : isOwner && !isMe
                                ? "Moderate / Delete"
                                : "Delete"}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {isMe && (
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: "50%",
                      background: "#4f46e5",
                      color: "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.82rem",
                      fontWeight: 700,
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                    title="You"
                  >
                    YOU
                  </div>
                )}
              </div>
            );
          })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input / Send Form */}
      <form onSubmit={handleSendMessage} style={{ marginTop: 16 }}>
        {sendError && (
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 8,
              padding: "10px 14px",
              color: "#991b1b",
              fontSize: "0.84rem",
              marginBottom: 10,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>⚠️ {sendError}</span>
            <button
              type="button"
              onClick={() => setSendError(null)}
              style={{
                background: "transparent",
                border: "none",
                color: "#991b1b",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              ✕
            </button>
          </div>
        )}

        <div style={{ position: "relative" }}>
          <textarea
            value={draftContent}
            onChange={(e) => setDraftContent(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e);
              }
            }}
            placeholder="Type a message to your travel group... (Press Enter to send, Shift+Enter for new line)"
            rows={3}
            disabled={sending}
            style={{
              width: "100%",
              padding: "12px 14px",
              borderRadius: 10,
              border: "1px solid #cbd5e1",
              fontSize: "0.92rem",
              fontFamily: "inherit",
              resize: "vertical",
              outline: "none",
              boxShadow: "inset 0 1px 2px rgba(0,0,0,0.04)",
              transition: "border 0.2s ease",
            }}
          />

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 8,
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            <span
              style={{
                fontSize: "0.76rem",
                color: draftContent.length > 2000 ? "#dc2626" : "#94a3b8",
              }}
            >
              {draftContent.length} / 2000 characters
            </span>

            <button
              type="submit"
              disabled={sending || !draftContent.trim() || draftContent.length > 2000}
              style={{
                background:
                  sending || !draftContent.trim()
                    ? "#94a3b8"
                    : "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
                color: "#ffffff",
                border: "none",
                borderRadius: 8,
                padding: "8px 22px",
                fontSize: "0.88rem",
                fontWeight: 700,
                cursor:
                  sending || !draftContent.trim() ? "not-allowed" : "pointer",
                boxShadow:
                  sending || !draftContent.trim()
                    ? "none"
                    : "0 2px 8px rgba(79, 70, 229, 0.35)",
                display: "flex",
                alignItems: "center",
                gap: 6,
                transition: "all 0.15s ease",
              }}
            >
              {sending ? (
                <>
                  <span>⏳</span> Sending...
                </>
              ) : (
                <>
                  <span>📨</span> Send Message
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
