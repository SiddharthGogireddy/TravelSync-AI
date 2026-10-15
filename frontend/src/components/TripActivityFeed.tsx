import { useState, useEffect } from "react";
import { getTripActivity } from "../services/api";
import type { ActivityEvent } from "../services/api";

interface TripActivityFeedProps {
  tripId: string;
}

export default function TripActivityFeed({ tripId }: TripActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [total, setTotal] = useState<number>(0);

  const PAGE_SIZE = 15;

  const loadFeed = async (initial = true, silent = false) => {
    if (initial) {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      setOffset(0);
    } else {
      setLoadingMore(true);
    }
    setError(null);

    try {
      const currentOffset = initial ? 0 : offset;
      const res = await getTripActivity(tripId, PAGE_SIZE, currentOffset);
      if (initial) {
        setActivities(res.activities || []);
      } else {
        setActivities((prev) => [...prev, ...(res.activities || [])]);
      }
      setTotal(res.total || 0);
      setHasMore(res.has_more);
      setOffset(currentOffset + (res.activities?.length || 0));
    } catch (err: any) {
      setError(err.message || "Failed to load activity feed.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (tripId) {
      loadFeed(true);
    }
  }, [tripId]);

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case "member_joined":
        return "👥";
      case "vote_submitted":
        return "🗳️";
      case "chat_message_posted":
        return "💬";
      case "attraction_comment_posted":
        return "📍";
      case "conflicts_resolved":
        return "⚡";
      case "expense_added":
        return "💰";
      case "itinerary_updated":
        return "🗺️";
      default:
        return "📌";
    }
  };

  const getEventBadgeColor = (eventType: string) => {
    switch (eventType) {
      case "member_joined":
        return { bg: "#ecfdf5", border: "#a7f3d0", text: "#065f46" };
      case "vote_submitted":
        return { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534" };
      case "chat_message_posted":
        return { bg: "#eef2ff", border: "#c7d2fe", text: "#3730a3" };
      case "attraction_comment_posted":
        return { bg: "#fdf4ff", border: "#f5d0fe", text: "#86198f" };
      case "conflicts_resolved":
        return { bg: "#fffbeb", border: "#fde68a", text: "#92400e" };
      case "expense_added":
        return { bg: "#f0fdfa", border: "#99f6e4", text: "#115e59" };
      default:
        return { bg: "#f8fafc", border: "#e2e8f0", text: "#334155" };
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
              <span>⚡</span> Activity Feed
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
              {total} event{total === 1 ? "" : "s"}
            </span>
          </div>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "0.85rem" }}>
            Real-time audit trail of trip votes, discussions, member joins, and itinerary updates.
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadFeed(true, true)}
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
          {refreshing ? "Refreshing..." : "Refresh Feed"}
        </button>
      </div>

      {/* Activities Timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>
            <div style={{ fontSize: "1.4rem", marginBottom: 8 }}>⏳</div>
            <p style={{ margin: 0, fontSize: "0.9rem" }}>Loading activity history...</p>
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
              onClick={() => loadFeed(true)}
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

        {!loading && !error && activities.length === 0 && (
          <div style={{ textAlign: "center", padding: "50px 20px", color: "#64748b" }}>
            <div style={{ fontSize: "2rem", marginBottom: 8 }}>📋</div>
            <div style={{ fontWeight: 600, color: "#334155", fontSize: "0.95rem" }}>
              No activity recorded yet
            </div>
            <p style={{ margin: "4px 0 0", fontSize: "0.84rem" }}>
              Votes, messages, new members, and itinerary updates will appear here automatically.
            </p>
          </div>
        )}

        {!loading &&
          !error &&
          activities.map((event) => {
            const colors = getEventBadgeColor(event.event_type);
            const icon = getEventIcon(event.event_type);

            return (
              <div
                key={event.id}
                style={{
                  background: "#ffffff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: "14px 18px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 14,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                  transition: "border 0.15s ease",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 10,
                    background: colors.bg,
                    border: `1px solid ${colors.border}`,
                    color: colors.text,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "1.1rem",
                    flexShrink: 0,
                    marginTop: 2,
                  }}
                >
                  {icon}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 3,
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <strong style={{ fontSize: "0.92rem", color: "#0f172a" }}>
                        {event.title}
                      </strong>
                      <span
                        style={{
                          background: colors.bg,
                          color: colors.text,
                          border: `1px solid ${colors.border}`,
                          padding: "1px 8px",
                          borderRadius: 8,
                          fontSize: "0.7rem",
                          fontWeight: 700,
                          textTransform: "uppercase",
                        }}
                      >
                        {event.event_type.replace(/_/g, " ")}
                      </span>
                    </div>

                    <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                      {formatTimestamp(event.created_at)}
                    </span>
                  </div>

                  <p
                    style={{
                      margin: "2px 0 6px",
                      fontSize: "0.86rem",
                      color: "#475569",
                      lineHeight: 1.45,
                    }}
                  >
                    {event.summary}
                  </p>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "0.76rem",
                      color: "#64748b",
                      marginTop: 4,
                    }}
                  >
                    <span>
                      Actor: <strong style={{ color: "#334155" }}>{event.actor_name || event.actor_id}</strong>
                    </span>

                    {event.link && (
                      <a
                        href={event.link}
                        style={{
                          color: "#4f46e5",
                          fontWeight: 600,
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        Jump to section →
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

        {/* Load More Button */}
        {hasMore && !loading && (
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <button
              type="button"
              onClick={() => loadFeed(false)}
              disabled={loadingMore}
              style={{
                background: "#f1f5f9",
                border: "1px solid #cbd5e1",
                color: "#334155",
                borderRadius: 8,
                padding: "8px 20px",
                fontSize: "0.84rem",
                fontWeight: 600,
                cursor: loadingMore ? "not-allowed" : "pointer",
              }}
            >
              {loadingMore ? "Loading more..." : "Load Older Activities"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
