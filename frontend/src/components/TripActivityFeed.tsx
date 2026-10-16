import { useState, useEffect } from "react";
import {
  Users,
  CheckCircle2,
  MessageSquare,
  MapPin,
  Zap,
  DollarSign,
  Calendar,
  Activity,
  RefreshCw,
  Loader2,
  AlertTriangle,
  ClipboardList,
} from "lucide-react";
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
      const resp = await getTripActivity(tripId, PAGE_SIZE, currentOffset);
      const items = resp.activities || (resp as any).events || [];

      if (initial) {
        setActivities(items);
      } else {
        setActivities((prev) => [...prev, ...items]);
      }

      setHasMore(resp.has_more);
      setTotal(resp.total ?? (resp as any).total_count ?? 0);
      setOffset(currentOffset + items.length);
    } catch (err: any) {
      console.error("Failed to load activity feed:", err);
      setError(err?.message || "Failed to load activity events.");
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
        return <Users size={16} />;
      case "vote_submitted":
        return <CheckCircle2 size={16} />;
      case "chat_message_posted":
        return <MessageSquare size={16} />;
      case "attraction_comment_posted":
        return <MapPin size={16} />;
      case "conflicts_resolved":
        return <Zap size={16} />;
      case "expense_added":
        return <DollarSign size={16} />;
      case "itinerary_updated":
        return <Calendar size={16} />;
      default:
        return <Activity size={16} />;
    }
  };

  const getEventBadgeColor = (eventType: string) => {
    switch (eventType) {
      case "member_joined":
        return { bg: "rgba(16, 185, 129, 0.12)", border: "rgba(16, 185, 129, 0.25)", text: "#10b981" };
      case "vote_submitted":
        return { bg: "rgba(16, 185, 129, 0.12)", border: "rgba(16, 185, 129, 0.25)", text: "#10b981" };
      case "chat_message_posted":
        return { bg: "var(--accent-bg)", border: "var(--accent-border)", text: "var(--accent)" };
      case "attraction_comment_posted":
        return { bg: "rgba(168, 85, 247, 0.12)", border: "rgba(168, 85, 247, 0.25)", text: "#a855f7" };
      case "conflicts_resolved":
        return { bg: "rgba(245, 158, 11, 0.12)", border: "rgba(245, 158, 11, 0.25)", text: "#f59e0b" };
      case "expense_added":
        return { bg: "rgba(14, 165, 233, 0.12)", border: "rgba(14, 165, 233, 0.25)", text: "#0ea5e9" };
      default:
        return { bg: "var(--code-bg)", border: "var(--border)", text: "var(--text-secondary)" };
    }
  };

  const formatTimestamp = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return (
        d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) +
        " · " +
        d.toLocaleDateString([], { month: "short", day: "numeric" })
      );
    } catch {
      return isoStr;
    }
  };

  return (
    <div
      style={{
        background: "var(--card-bg)",
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "24px",
        boxShadow: "var(--shadow)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h3
              style={{
                margin: 0,
                fontSize: "1.25rem",
                color: "var(--text-h)",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Activity size={20} style={{ color: "var(--accent)" }} />
              <span>Activity Feed</span>
            </h3>
            <span
              style={{
                background: "var(--code-bg)",
                color: "var(--text-muted)",
                padding: "3px 10px",
                borderRadius: 12,
                fontSize: "0.78rem",
                fontWeight: 600,
                border: "1px solid var(--border)",
              }}
            >
              {total} event{total === 1 ? "" : "s"}
            </span>
          </div>
          <p style={{ margin: "4px 0 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Real-time audit trail of trip votes, discussions, member joins, and itinerary updates.
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadFeed(true, true)}
          disabled={refreshing || loading}
          style={{
            background: "var(--code-bg)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
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
          <RefreshCw size={14} style={{ animation: refreshing ? "spin 1s linear infinite" : "none" }} />
          <span>{refreshing ? "Refreshing..." : "Refresh Feed"}</span>
        </button>
      </div>

      {/* Activities Timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
            <p style={{ margin: 0, fontSize: "0.9rem" }}>Loading activity history...</p>
          </div>
        )}

        {!loading && error && (
          <div
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              borderRadius: 8,
              padding: "14px",
              textAlign: "center",
              color: "#ef4444",
              fontSize: "0.88rem",
            }}
          >
            <p style={{ margin: "0 0 8px", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
              <AlertTriangle size={15} />
              <span>{error}</span>
            </p>
            <button
              type="button"
              onClick={() => loadFeed(true)}
              style={{
                background: "#ef4444",
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
          <div style={{ textAlign: "center", padding: "50px 20px", color: "var(--text-muted)" }}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 8 }}>
              <ClipboardList size={32} style={{ color: "var(--text-muted)" }} />
            </div>
            <div style={{ fontWeight: 600, color: "var(--text-h)", fontSize: "0.95rem" }}>
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
                  background: "var(--card-bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: "14px 18px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 14,
                  boxShadow: "var(--shadow)",
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
                      <strong style={{ fontSize: "0.92rem", color: "var(--text-h)" }}>
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

                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {formatTimestamp(event.created_at)}
                    </span>
                  </div>

                  <p
                    style={{
                      margin: "2px 0 6px",
                      fontSize: "0.86rem",
                      color: "var(--text-secondary)",
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
                      color: "var(--text-muted)",
                      marginTop: 4,
                    }}
                  >
                    <span>
                      Actor: <strong style={{ color: "var(--text-h)" }}>{event.actor_name || event.actor_id}</strong>
                    </span>

                    {event.link && (
                      <a
                        href={event.link}
                        style={{
                          color: "var(--accent)",
                          fontWeight: 600,
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        Jump to section &rarr;
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
                background: "var(--code-bg)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
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
