import React, { useState, useEffect, useRef } from "react";
import { Bell, Loader2, AlertTriangle, Inbox, Check } from "lucide-react";
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
          background: isOpen ? "var(--accent-bg)" : "var(--card-bg)",
          border: isOpen ? "1px solid var(--accent)" : "1px solid var(--border)",
          borderRadius: "50%",
          width: 38,
          height: 38,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: "var(--shadow)",
          transition: "all 0.15s ease",
          color: "var(--text-secondary)",
        }}
      >
        <Bell size={18} />
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
              border: "2px solid var(--card-bg)",
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
            background: "var(--dropdown-bg)",
            borderRadius: 14,
            boxShadow: "var(--shadow-lg)",
            border: "1px solid var(--dropdown-border)",
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
              borderBottom: "1px solid var(--border)",
              background: "var(--code-bg)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <strong style={{ fontSize: "0.95rem", color: "var(--text-h)" }}>
                Notifications
              </strong>
              {unreadCount > 0 && (
                <span
                  style={{
                    background: "rgba(239, 68, 68, 0.15)",
                    color: "#ef4444",
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
                  color: "var(--accent)",
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
              borderBottom: "1px solid var(--border)",
              padding: "4px 8px",
              background: "var(--code-bg)",
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
                background: !filterUnread ? "var(--card-bg)" : "transparent",
                color: !filterUnread ? "var(--text-h)" : "var(--text-muted)",
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
                background: filterUnread ? "var(--card-bg)" : "transparent",
                color: filterUnread ? "var(--text-h)" : "var(--text-muted)",
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
              <div style={{ textAlign: "center", padding: "30px 16px", color: "var(--text-muted)", fontSize: "0.86rem", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
                <span>Loading notifications...</span>
              </div>
            )}

            {!loading && error && (
              <div style={{ padding: "16px", textAlign: "center", color: "#ef4444", fontSize: "0.82rem", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <AlertTriangle size={15} />
                <span>{error}</span>
              </div>
            )}

            {!loading && !error && notifications.length === 0 && (
              <div style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-muted)" }}>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: 8 }}>
                  <Inbox size={32} style={{ color: "var(--text-muted)" }} />
                </div>
                <div style={{ fontWeight: 600, color: "var(--text-h)", fontSize: "0.88rem" }}>
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
                    borderBottom: "1px solid var(--border)",
                    background: notif.is_read ? "var(--card-bg)" : "var(--accent-bg)",
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
                      <strong style={{ fontSize: "0.84rem", color: notif.is_read ? "var(--text-secondary)" : "var(--text-h)" }}>
                        {notif.title}
                      </strong>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                        {formatTimestamp(notif.created_at)}
                      </span>
                    </div>

                    <p style={{ margin: "3px 0 6px", fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                      {notif.message}
                    </p>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      {notif.link ? (
                        <a
                          href={notif.link}
                          onClick={() => setIsOpen(false)}
                          style={{
                            color: "var(--accent)",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            textDecoration: "none",
                          }}
                        >
                          View details &rarr;
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
                            color: "#10b981",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            cursor: "pointer",
                            padding: "2px 6px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <Check size={12} />
                          <span>Mark read</span>
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
