import React, { useState, useEffect, useRef } from "react";
import {
  getUserNotifications,
  getUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
} from "../services/api";
import type { UserNotification } from "../services/api";

interface NotificationCenterProps {
  tripId?: string;
}

export default function NotificationCenter({ tripId }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filterUnread, setFilterUnread] = useState<boolean>(false);

  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const fetchUnread = async () => {
    try {
      const count = await getUnreadNotificationCount(tripId);
      setUnreadCount(count);
    } catch {
      // ignore background poll error
    }
  };

  const loadNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getUserNotifications({
        trip_id: tripId,
        is_read: filterUnread ? false : undefined,
        limit: 50,
      });
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch (err: any) {
      setError(err.message || "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
    // Poll unread count periodically (every 30 seconds)
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, [tripId]);

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen, filterUnread, tripId]);

  // Handle outside click to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkOne = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err: any) {
      alert(err.message || "Failed to mark as read");
    }
  };

  const handleMarkAll = async () => {
    try {
      await markAllNotificationsRead(tripId);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err: any) {
      alert(err.message || "Failed to mark all as read");
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
    <div style={{ position: "relative", display: "inline-block" }} ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={`Notifications (${unreadCount} unread)`}
        title="View in-app notifications"
        style={{
          position: "relative",
          background: isOpen ? "#ede9fe" : "#ffffff",
          border: isOpen ? "1px solid #818cf8" : "1px solid #cbd5e1",
          borderRadius: "50%",
          width: 38,
          height: 38,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
          transition: "all 0.15s ease",
        }}
      >
        <span style={{ fontSize: "1.1rem" }}>🔔</span>
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: -3,
              right: -3,
              background: "#ef4444",
              color: "#ffffff",
              borderRadius: "10px",
              padding: "1px 6px",
              fontSize: "0.68rem",
              fontWeight: 800,
              border: "2px solid #ffffff",
              boxShadow: "0 1px 3px rgba(239, 68, 68, 0.4)",
            }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Card */}
      {isOpen && (
        <div
          role="region"
          aria-label="Notifications panel"
          style={{
            position: "absolute",
            top: 46,
            right: 0,
            width: 360,
            maxWidth: "90vw",
            background: "#ffffff",
            borderRadius: 14,
            boxShadow: "0 10px 25px -5px rgba(0,0,0,0.18), 0 8px 10px -6px rgba(0,0,0,0.1)",
            border: "1px solid #e2e8f0",
            zIndex: 1000,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            maxHeight: 480,
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid #f1f5f9",
              background: "#f8fafc",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <strong style={{ fontSize: "0.95rem", color: "#0f172a" }}>
                Notifications
              </strong>
              {unreadCount > 0 && (
                <span
                  style={{
                    background: "#fee2e2",
                    color: "#991b1b",
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: "0.72rem",
                    fontWeight: 700,
                  }}
                >
                  {unreadCount} unread
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAll}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#4f46e5",
                  fontSize: "0.76rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Filter Tabs */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid #f1f5f9",
              padding: "4px 8px",
              background: "#ffffff",
              gap: 4,
            }}
          >
            <button
              type="button"
              onClick={() => setFilterUnread(false)}
              style={{
                flex: 1,
                padding: "6px",
                border: "none",
                borderRadius: 6,
                background: !filterUnread ? "#f1f5f9" : "transparent",
                color: !filterUnread ? "#0f172a" : "#64748b",
                fontSize: "0.78rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setFilterUnread(true)}
              style={{
                flex: 1,
                padding: "6px",
                border: "none",
                borderRadius: 6,
                background: filterUnread ? "#f1f5f9" : "transparent",
                color: filterUnread ? "#0f172a" : "#64748b",
                fontSize: "0.78rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Unread only
            </button>
          </div>

          {/* List items */}
          <div
            style={{
              overflowY: "auto",
              flex: 1,
              display: "flex",
              flexDirection: "column",
            }}
          >
            {loading && (
              <div style={{ textAlign: "center", padding: "30px 16px", color: "#64748b", fontSize: "0.86rem" }}>
                ⏳ Loading notifications...
              </div>
            )}

            {!loading && error && (
              <div style={{ padding: "16px", textAlign: "center", color: "#dc2626", fontSize: "0.82rem" }}>
                ⚠️ {error}
              </div>
            )}

            {!loading && !error && notifications.length === 0 && (
              <div style={{ padding: "40px 16px", textAlign: "center", color: "#64748b" }}>
                <div style={{ fontSize: "1.6rem", marginBottom: 4 }}>📭</div>
                <div style={{ fontWeight: 600, color: "#334155", fontSize: "0.88rem" }}>
                  {filterUnread ? "No unread notifications" : "No notifications yet"}
                </div>
                <p style={{ margin: "2px 0 0", fontSize: "0.76rem" }}>
                  You're all caught up!
                </p>
              </div>
            )}

            {!loading &&
              !error &&
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  style={{
                    padding: "12px 16px",
                    borderBottom: "1px solid #f1f5f9",
                    background: notif.is_read ? "#ffffff" : "#f0fdf4",
                    display: "flex",
                    gap: 10,
                    alignItems: "flex-start",
                    transition: "background 0.15s ease",
                  }}
                >
                  {/* Unread dot */}
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: notif.is_read ? "transparent" : "#22c55e",
                      flexShrink: 0,
                      marginTop: 6,
                    }}
                  />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                      <strong style={{ fontSize: "0.84rem", color: notif.is_read ? "#334155" : "#0f172a" }}>
                        {notif.title}
                      </strong>
                      <span style={{ fontSize: "0.7rem", color: "#94a3b8", whiteSpace: "nowrap" }}>
                        {formatTimestamp(notif.created_at)}
                      </span>
                    </div>

                    <p style={{ margin: "3px 0 6px", fontSize: "0.78rem", color: "#475569", lineHeight: 1.4 }}>
                      {notif.message}
                    </p>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      {notif.link ? (
                        <a
                          href={notif.link}
                          onClick={() => setIsOpen(false)}
                          style={{
                            color: "#4f46e5",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            textDecoration: "none",
                          }}
                        >
                          View details →
                        </a>
                      ) : (
                        <span />
                      )}

                      {!notif.is_read && (
                        <button
                          type="button"
                          onClick={(e) => handleMarkOne(notif.id, e)}
                          title="Mark as read"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "#16a34a",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            cursor: "pointer",
                            padding: "2px 6px",
                          }}
                        >
                          ✓ Mark read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
