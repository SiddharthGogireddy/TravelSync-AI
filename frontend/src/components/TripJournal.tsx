import React, { useState, useEffect, useRef } from "react";
import {
  BookOpen,
  Download,
  Loader2,
  Plus,
  FileText,
  Image as ImageIcon,
  Users,
  Lock,
  Edit3,
  Trash2,
  MapPin,
  Sparkles,
  X,
  Camera,
  Search,
  AlertTriangle,
} from "lucide-react";
import {
  getJournalEntries,
  createJournalEntry,
  uploadJournalPhoto,
  updateJournalEntry,
  deleteJournalEntry,
  getMemoryAlbum,
  exportJournalPdf,
  API_BASE,
  type JournalEntry,
  type AlbumItem,
} from "../services/api";
import { getCurrentUserId, getAuthToken } from "../services/identity";

interface TripJournalProps {
  tripId: string;
  userRole?: string;
  tripDays?: number;
  places?: Array<{ name: string }>;
}

export default function TripJournal({
  tripId,
  userRole = "editor",
  tripDays = 3,
  places = [],
}: TripJournalProps) {
  const currentUserId = getCurrentUserId();
  const token = getAuthToken();

  // Active view: 'journal' (Chronicle entries) vs 'album' (Photo memory cards)
  const [activeView, setActiveView] = useState<"journal" | "album">("journal");

  // Journal entries state
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Album state
  const [albumItems, setAlbumItems] = useState<AlbumItem[]>([]);
  const [albumTotal, setAlbumTotal] = useState(0);
  const [albumLoading, setAlbumLoading] = useState(false);
  const [albumError, setAlbumError] = useState<string | null>(null);

  // Export PDF state
  const [exportingPdf, setExportingPdf] = useState(false);

  // Filters
  const [privacyFilter, setPrivacyFilter] = useState<"all" | "shared" | "private">("all");
  const [dayFilter, setDayFilter] = useState<number | "all">("all");

  // Editor modal/inline state
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [dayNumber, setDayNumber] = useState<number | "">("");
  const [attractionName, setAttractionName] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);

  // Photo attachment
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [existingPhotoUrl, setExistingPhotoUrl] = useState<string | null>(null);
  const [existingPhotoFilename, setExistingPhotoFilename] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [lightboxPhoto, setLightboxPhoto] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadEntries = async () => {
    if (!tripId) return;
    setLoading(true);
    setError(null);
    try {
      const params: { day_number?: number; limit: number } = { limit: 100 };
      if (dayFilter !== "all") {
        params.day_number = dayFilter;
      }
      const data = await getJournalEntries(tripId, params);
      setEntries(data.entries || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err?.message || "Failed to load journal entries");
    } finally {
      setLoading(false);
    }
  };

  const loadAlbum = async () => {
    if (!tripId) return;
    setAlbumLoading(true);
    setAlbumError(null);
    try {
      const params: { day_number?: number; limit: number } = { limit: 100 };
      if (dayFilter !== "all") {
        params.day_number = dayFilter;
      }
      const data = await getMemoryAlbum(tripId, params);
      setAlbumItems(data.items || []);
      setAlbumTotal(data.total || 0);
    } catch (err: any) {
      setAlbumError(err?.message || "Failed to load memory album");
    } finally {
      setAlbumLoading(false);
    }
  };

  useEffect(() => {
    loadEntries();
    if (activeView === "album") {
      loadAlbum();
    }
  }, [tripId, dayFilter, activeView]);

  const handleExportPdf = async () => {
    if (!tripId || exportingPdf) return;
    setExportingPdf(true);
    try {
      const dayParam = dayFilter !== "all" ? dayFilter : undefined;
      const blob = await exportJournalPdf(tripId, dayParam);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const daySuffix = dayParam ? `_Day${dayParam}` : "";
      a.download = `TripJournal_${tripId.slice(0, 8)}${daySuffix}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err?.message || "Failed to export journal PDF");
    } finally {
      setExportingPdf(false);
    }
  };

  const handleOpenNewEditor = () => {
    setEditingEntryId(null);
    setTitle("");
    setContent("");
    setDayNumber("");
    setAttractionName("");
    setIsPrivate(false);
    setSelectedFile(null);
    setPreviewUrl(null);
    setExistingPhotoUrl(null);
    setExistingPhotoFilename(null);
    setFormError(null);
    setIsEditorOpen(true);
  };

  const handleOpenEditEditor = (entry: JournalEntry) => {
    setEditingEntryId(entry.id);
    setTitle(entry.title || "");
    setContent(entry.content || "");
    setDayNumber(entry.day_number || "");
    setAttractionName(entry.attraction_name || "");
    setIsPrivate(entry.is_private);
    setSelectedFile(null);
    setPreviewUrl(null);
    setExistingPhotoUrl(entry.photo_url || null);
    setExistingPhotoFilename(entry.photo_filename || null);
    setFormError(null);
    setIsEditorOpen(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (max 5MB)
    const MAX_SIZE = 5 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setFormError("Selected photo exceeds the 5MB file size limit");
      return;
    }

    // Validate extension
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    const allowed = [".jpg", ".jpeg", ".png", ".webp", ".gif"];
    if (!allowed.includes(ext)) {
      setFormError(`Unsupported file format. Please upload JPG, PNG, WebP, or GIF.`);
      return;
    }

    setFormError(null);
    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleRemovePhoto = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setExistingPhotoUrl(null);
    setExistingPhotoFilename(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setFormError("Please enter some journal text or memory reflection.");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      let finalPhotoUrl = existingPhotoUrl;
      let finalPhotoFilename = existingPhotoFilename;

      // 1. Upload photo if selected
      if (selectedFile) {
        const uploadResult = await uploadJournalPhoto(tripId, selectedFile);
        finalPhotoUrl = uploadResult.photo_url;
        finalPhotoFilename = uploadResult.photo_filename;
      }

      const payload = {
        title: title.trim() || undefined,
        content: content.trim(),
        day_number: typeof dayNumber === "number" ? dayNumber : undefined,
        attraction_name: attractionName.trim() || undefined,
        photo_url: finalPhotoUrl || undefined,
        photo_filename: finalPhotoFilename || undefined,
        is_private: isPrivate,
      };

      if (editingEntryId) {
        await updateJournalEntry(tripId, editingEntryId, payload);
      } else {
        await createJournalEntry(tripId, payload);
      }

      setIsEditorOpen(false);
      await loadEntries();
      if (activeView === "album") {
        await loadAlbum();
      }
    } catch (err: any) {
      setFormError(err?.message || "Failed to save journal entry");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (entryId: string) => {
    if (!window.confirm("Are you sure you want to delete this journal memory?")) {
      return;
    }
    setDeletingId(entryId);
    try {
      await deleteJournalEntry(tripId, entryId);
      await loadEntries();
      if (activeView === "album") {
        await loadAlbum();
      }
    } catch (err: any) {
      alert(err?.message || "Failed to delete entry");
    } finally {
      setDeletingId(null);
    }
  };

  // Filter entries in memory for privacy tab
  const filteredEntries = entries.filter((entry) => {
    if (privacyFilter === "shared") return !entry.is_private;
    if (privacyFilter === "private") return entry.is_private;
    return true;
  });

  // Filter album items in memory for privacy tab
  const filteredAlbumItems = albumItems.filter((item) => {
    if (privacyFilter === "shared") return !item.is_private;
    if (privacyFilter === "private") return item.is_private;
    return true;
  });

  // Helper to build authenticated photo URL
  const getAuthenticatedPhotoSrc = (relativeUrl: string) => {
    if (!relativeUrl) return "";
    const cleanUrl = relativeUrl.startsWith("http") ? relativeUrl : `${API_BASE}${relativeUrl}`;
    return token ? `${cleanUrl}${cleanUrl.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}` : cleanUrl;
  };

  const dayNumbersList = Array.from({ length: Math.max(1, tripDays) }, (_, i) => i + 1);

  return (
    <div
      id="section-journal"
      style={{
        background: "var(--card-bg)",
        borderRadius: 24,
        padding: "32px",
        boxShadow: "var(--card-shadow, 0 8px 30px rgba(0,0,0,0.06))",
        border: "1px solid var(--border)",
        marginTop: 24,
        marginBottom: 32,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 16,
          marginBottom: 20,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <BookOpen size={28} color="var(--accent)" />
            <h2
              style={{
                fontSize: "1.6rem",
                fontWeight: 700,
                color: "var(--text-h)",
                margin: 0,
                letterSpacing: "-0.02em",
              }}
            >
              Travel Memories & Trip Journal
            </h2>
          </div>
          <p style={{ color: "var(--text-muted)", margin: "6px 0 0 0", fontSize: "0.95rem" }}>
            Reflections, trip chronicle, and photo album. Export your authenticated travel journal as a PDF.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={handleExportPdf}
            disabled={exportingPdf}
            title="Download formatted PDF trip journal"
            style={{
              background: "var(--bg-alt)",
              color: "var(--accent)",
              border: "1px solid var(--border)",
              borderRadius: 14,
              padding: "10px 18px",
              fontSize: "0.9rem",
              fontWeight: 600,
              cursor: exportingPdf ? "not-allowed" : "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
              transition: "all 0.2s ease",
            }}
          >
            {exportingPdf ? (
              <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
            ) : (
              <Download size={16} />
            )}
            {exportingPdf ? "Generating PDF..." : "Export Journal PDF"}
          </button>

          <button
            onClick={handleOpenNewEditor}
            style={{
              background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
              color: "#ffffff",
              border: "none",
              borderRadius: 14,
              padding: "10px 20px",
              fontSize: "0.92rem",
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              boxShadow: "0 4px 14px rgba(37,99,235,0.25)",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-1px)")}
            onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
          >
            <Plus size={16} /> Add Memory
          </button>
        </div>
      </div>

      {/* View Switcher: Journal Chronicle vs Memory Album */}
      <div
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 20,
          borderBottom: "1px solid var(--border)",
          paddingBottom: 12,
        }}
      >
        <button
          onClick={() => setActiveView("journal")}
          style={{
            background: activeView === "journal" ? "var(--accent)" : "var(--bg-alt)",
            color: activeView === "journal" ? "#ffffff" : "var(--text-muted)",
            border: "1px solid " + (activeView === "journal" ? "var(--accent)" : "var(--border)"),
            borderRadius: 12,
            padding: "8px 18px",
            fontSize: "0.9rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
        >
          <FileText size={16} /> Journal Chronicle ({total})
        </button>

        <button
          onClick={() => setActiveView("album")}
          style={{
            background: activeView === "album" ? "var(--accent)" : "var(--bg-alt)",
            color: activeView === "album" ? "#ffffff" : "var(--text-muted)",
            border: "1px solid " + (activeView === "album" ? "var(--accent)" : "var(--border)"),
            borderRadius: 12,
            padding: "8px 18px",
            fontSize: "0.9rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
        >
          <ImageIcon size={16} /> Memory Album ({albumTotal || entries.filter((e) => e.photo_url).length})
        </button>
      </div>

      {/* Filter Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          padding: "14px 18px",
          background: "var(--bg-alt)",
          borderRadius: 16,
          border: "1px solid var(--border)",
          marginBottom: 24,
        }}
      >
        {/* Privacy Tabs */}
        <div style={{ display: "flex", gap: 6 }}>
          {[
            { id: "all", label: activeView === "journal" ? `All Memories (${total})` : `All Photos (${albumTotal})`, icon: null },
            { id: "shared", label: "Shared", icon: <Users size={14} /> },
            { id: "private", label: "Private to Me", icon: <Lock size={14} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setPrivacyFilter(tab.id as any)}
              style={{
                background: privacyFilter === tab.id ? "var(--accent)" : "var(--card-bg)",
                color: privacyFilter === tab.id ? "#ffffff" : "var(--text)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "6px 14px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                transition: "all 0.15s ease",
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Day Filter Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 500 }}>
            Filter Day:
          </span>
          <select
            value={dayFilter}
            onChange={(e) => setDayFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            style={{
              padding: "6px 12px",
              borderRadius: 10,
              border: "1px solid var(--input-border)",
              fontSize: "0.85rem",
              color: "var(--input-text)",
              background: "var(--input-bg)",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            <option value="all">All Itinerary Days</option>
            {dayNumbersList.map((d) => (
              <option key={d} value={d}>
                Day {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Entry Editor Modal */}
      {isEditorOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 16,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !submitting) {
              setIsEditorOpen(false);
            }
          }}
        >
          <div
            style={{
              background: "var(--card-bg)",
              borderRadius: 20,
              padding: "28px",
              maxWidth: 580,
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              boxShadow: "0 20px 40px rgba(0,0,0,0.3)",
              border: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 20,
              }}
            >
              <h3 style={{ margin: 0, fontSize: "1.3rem", fontWeight: 700, color: "var(--text-h)", display: "flex", alignItems: "center", gap: 8 }}>
                {editingEntryId ? <Edit3 size={20} color="var(--accent)" /> : <Sparkles size={20} color="var(--accent)" />}
                {editingEntryId ? "Edit Journal Memory" : "New Travel Memory"}
              </h3>
              <button
                type="button"
                onClick={() => setIsEditorOpen(false)}
                disabled={submitting}
                style={{
                  background: "var(--bg-alt)",
                  border: "1px solid var(--border)",
                  borderRadius: "50%",
                  width: 32,
                  height: 32,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-muted)",
                }}
              >
                <X size={16} />
              </button>
            </div>

            {formError && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(239, 68, 68, 0.1)",
                  color: "#ef4444",
                  fontSize: "0.88rem",
                  marginBottom: 16,
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <AlertTriangle size={16} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 6 }}>
                  Title / Headline (optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Sunset view from the cliffs, Best pasta ever..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={200}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: "1px solid var(--input-border)",
                    background: "var(--input-bg)",
                    color: "var(--input-text)",
                    fontSize: "0.95rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 6 }}>
                    Itinerary Day
                  </label>
                  <select
                    value={dayNumber}
                    onChange={(e) => setDayNumber(e.target.value === "" ? "" : Number(e.target.value))}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: "1px solid var(--input-border)",
                      fontSize: "0.9rem",
                      background: "var(--input-bg)",
                      color: "var(--input-text)",
                    }}
                  >
                    <option value="">General Trip</option>
                    {dayNumbersList.map((d) => (
                      <option key={d} value={d}>
                        Day {d}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 6 }}>
                    Attraction (optional)
                  </label>
                  <input
                    type="text"
                    list="trip-places-list"
                    placeholder="e.g. Eiffel Tower, Marina Beach..."
                    value={attractionName}
                    onChange={(e) => setAttractionName(e.target.value)}
                    maxLength={200}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: 10,
                      border: "1px solid var(--input-border)",
                      background: "var(--input-bg)",
                      color: "var(--input-text)",
                      fontSize: "0.9rem",
                      boxSizing: "border-box",
                    }}
                  />
                  <datalist id="trip-places-list">
                    {places.map((p, idx) => (
                      <option key={idx} value={p.name} />
                    ))}
                  </datalist>
                </div>
              </div>

              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: 12,
                  background: isPrivate ? "rgba(124, 58, 237, 0.1)" : "rgba(16, 185, 129, 0.1)",
                  border: isPrivate ? "1px solid rgba(124, 58, 237, 0.3)" : "1px solid rgba(16, 185, 129, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem", color: isPrivate ? "#8b5cf6" : "#10b981", display: "flex", alignItems: "center", gap: 6 }}>
                    {isPrivate ? <Lock size={15} /> : <Users size={15} />}
                    {isPrivate ? "Private Memory (Only you can view)" : "Shared Memory (Visible to trip group)"}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 2 }}>
                    {isPrivate
                      ? "Never shared with other members or shown in their PDF exports."
                      : "Trip members can read this memory, view in album, and include in PDF exports."}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setIsPrivate(!isPrivate)}
                  style={{
                    background: isPrivate ? "#7c3aed" : "#16a34a",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 8,
                    padding: "6px 12px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  {isPrivate ? "Make Shared" : "Make Private"}
                </button>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 6 }}>
                  Memory / Reflection <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <textarea
                  rows={5}
                  placeholder="Write your travel thoughts, stories, highlights, favorite meals, or personal reflection..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  maxLength={10000}
                  required
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 10,
                    border: "1px solid var(--input-border)",
                    background: "var(--input-bg)",
                    color: "var(--input-text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.5,
                    fontFamily: "inherit",
                    boxSizing: "border-box",
                  }}
                />
                <div style={{ textAlign: "right", fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                  {content.length} / 10,000 characters
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--input-label)", marginBottom: 6 }}>
                  Photo Memory (Max 5MB • JPG, PNG, WebP)
                </label>

                {previewUrl || existingPhotoUrl ? (
                  <div
                    style={{
                      position: "relative",
                      display: "inline-block",
                      borderRadius: 12,
                      overflow: "hidden",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <img
                      src={previewUrl || getAuthenticatedPhotoSrc(existingPhotoUrl!)}
                      alt="Attachment preview"
                      style={{
                        width: 180,
                        height: 120,
                        objectFit: "cover",
                        display: "block",
                      }}
                    />
                    <button
                      type="button"
                      onClick={handleRemovePhoto}
                      title="Remove photo"
                      style={{
                        position: "absolute",
                        top: 6,
                        right: 6,
                        background: "rgba(0,0,0,0.7)",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "50%",
                        width: 26,
                        height: 26,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/jpeg,image/png,image/webp,image/gif"
                      onChange={handleFileChange}
                      style={{ display: "none" }}
                      id="journal-photo-upload"
                    />
                    <label
                      htmlFor="journal-photo-upload"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 16px",
                        borderRadius: 10,
                        border: "1px dashed var(--border)",
                        background: "var(--bg-alt)",
                        color: "var(--text)",
                        fontSize: "0.88rem",
                        fontWeight: 500,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <Camera size={16} /> Select Photo to Attach
                    </label>
                  </div>
                )}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => setIsEditorOpen(false)}
                  disabled={submitting}
                  style={{
                    padding: "10px 18px",
                    borderRadius: 10,
                    border: "1px solid var(--border)",
                    background: "var(--bg-alt)",
                    color: "var(--text)",
                    fontWeight: 600,
                    fontSize: "0.9rem",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  style={{
                    padding: "10px 22px",
                    borderRadius: 10,
                    border: "none",
                    background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
                    color: "#ffffff",
                    fontWeight: 600,
                    fontSize: "0.9rem",
                    cursor: submitting ? "not-allowed" : "pointer",
                    boxShadow: "0 4px 12px rgba(37,99,235,0.25)",
                    opacity: submitting ? 0.7 : 1,
                  }}
                >
                  {submitting ? "Saving..." : editingEntryId ? "Update Memory" : "Save Memory"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Lightbox Modal */}
      {lightboxPhoto && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.9)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10000,
            padding: 24,
          }}
          onClick={() => setLightboxPhoto(null)}
        >
          <div style={{ position: "relative", maxWidth: "90vw", maxHeight: "90vh" }}>
            <img
              src={getAuthenticatedPhotoSrc(lightboxPhoto)}
              alt="Expanded photo memory"
              style={{
                maxWidth: "100%",
                maxHeight: "85vh",
                borderRadius: 12,
                boxShadow: "0 25px 50px rgba(0,0,0,0.5)",
                display: "block",
              }}
            />
            <button
              onClick={() => setLightboxPhoto(null)}
              style={{
                position: "absolute",
                top: -16,
                right: -16,
                background: "var(--card-bg)",
                color: "var(--text)",
                border: "1px solid var(--border)",
                borderRadius: "50%",
                width: 36,
                height: 36,
                cursor: "pointer",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 1: Memory Album (Photo Cards Grid) */}
      {/* ========================================================================= */}
      {activeView === "album" && (
        <div>
          {albumLoading ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  border: "3px solid #e2e8f0",
                  borderTopColor: "#0ea5e9",
                  borderRadius: "50%",
                  margin: "0 auto 12px",
                  animation: "spin 1s linear infinite",
                }}
              />
              <p style={{ margin: 0, fontSize: "0.9rem" }}>Loading memory album photos...</p>
            </div>
          ) : albumError ? (
            <div
              style={{
                padding: 20,
                borderRadius: 14,
                background: "#fee2e2",
                color: "#991b1b",
                textAlign: "center",
              }}
            >
              <p style={{ margin: "0 0 10px 0", fontWeight: 600 }}>Failed to load album: {albumError}</p>
              <button
                onClick={loadAlbum}
                style={{
                  padding: "6px 14px",
                  borderRadius: 8,
                  border: "none",
                  background: "#dc2626",
                  color: "#ffffff",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Retry
              </button>
            </div>
          ) : filteredAlbumItems.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "48px 24px",
                background: "var(--card-bg)",
                borderRadius: 18,
                border: "1px dashed var(--border)",
              }}
            >
              <div style={{ marginBottom: 12, opacity: 0.5 }}>
                <ImageIcon size={48} />
              </div>
              <h3 style={{ margin: "0 0 6px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
                No photos in memory album yet
              </h3>
              <p style={{ margin: "0 auto 18px", maxWidth: 420, color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Attach photos when creating journal memories to build a visual timeline of your journey!
              </p>
              <button
                onClick={handleOpenNewEditor}
                style={{
                  background: "var(--accent)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 12,
                  padding: "8px 18px",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Plus size={16} /> Add Photo Memory
              </button>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                gap: 20,
              }}
            >
              {filteredAlbumItems.map((item) => {
                const dateStr = item.created_at
                  ? new Date(item.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  : "";

                return (
                  <div
                    key={item.id}
                    style={{
                      background: "var(--card-bg)",
                      borderRadius: 18,
                      overflow: "hidden",
                      border: "1px solid var(--border)",
                      boxShadow: "var(--card-shadow, 0 4px 16px rgba(0,0,0,0.04))",
                      display: "flex",
                      flexDirection: "column",
                      transition: "transform 0.2s ease, box-shadow 0.2s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-2px)";
                      e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.08)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "translateY(0)";
                      e.currentTarget.style.boxShadow = "var(--card-shadow, 0 4px 16px rgba(0,0,0,0.04))";
                    }}
                  >
                    {/* Photo Container */}
                    <div
                      style={{
                        position: "relative",
                        height: 200,
                        background: "var(--bg-alt)",
                        cursor: "pointer",
                        overflow: "hidden",
                      }}
                      onClick={() => setLightboxPhoto(item.photo_url)}
                    >
                      <img
                        src={getAuthenticatedPhotoSrc(item.photo_url)}
                        alt={item.title || "Trip album photo"}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          display: "block",
                          transition: "transform 0.3s ease",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.04)")}
                        onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                      />

                      {/* Top Overlay Badges */}
                      <div
                        style={{
                          position: "absolute",
                          top: 10,
                          left: 10,
                          right: 10,
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          pointerEvents: "none",
                        }}
                      >
                        {item.day_number ? (
                          <span
                            style={{
                              background: "rgba(15, 23, 42, 0.75)",
                              color: "#ffffff",
                              fontSize: "0.72rem",
                              fontWeight: 700,
                              padding: "3px 8px",
                              borderRadius: 8,
                              backdropFilter: "blur(4px)",
                            }}
                          >
                            Day {item.day_number}
                          </span>
                        ) : <span />}

                        <span
                          style={{
                            background: item.is_private ? "rgba(124, 58, 237, 0.85)" : "rgba(16, 185, 129, 0.85)",
                            color: "#ffffff",
                            fontSize: "0.72rem",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: 8,
                            backdropFilter: "blur(4px)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          {item.is_private ? <Lock size={11} /> : <Users size={11} />}
                          {item.is_private ? "Private" : "Shared"}
                        </span>
                      </div>
                    </div>

                    {/* Card Content Footer */}
                    <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
                          {item.author_name || item.author_id}
                        </span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{dateStr}</span>
                      </div>

                      {item.attraction_name && (
                        <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--accent)", display: "flex", alignItems: "center", gap: 4 }}>
                          <MapPin size={12} /> {item.attraction_name}
                        </div>
                      )}

                      {item.title && (
                        <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-h)" }}>
                          {item.title}
                        </div>
                      )}

                      <p
                        style={{
                          margin: 0,
                          fontSize: "0.85rem",
                          color: "var(--text)",
                          lineHeight: 1.4,
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {item.content}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 2: Journal Chronicle (Chronological Cards) */}
      {/* ========================================================================= */}
      {activeView === "journal" && (
        <div>
          {loading ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>
              <Loader2 size={32} style={{ animation: "spin 1s linear infinite", margin: "0 auto 12px" }} />
              <p style={{ margin: 0, fontSize: "0.9rem" }}>Loading travel memories...</p>
            </div>
          ) : error ? (
            <div
              style={{
                padding: 20,
                borderRadius: 14,
                background: "rgba(239, 68, 68, 0.1)",
                color: "#ef4444",
                textAlign: "center",
                border: "1px solid rgba(239, 68, 68, 0.3)",
              }}
            >
              <p style={{ margin: "0 0 10px 0", fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <AlertTriangle size={16} /> Failed to load journal entries: {error}
              </p>
              <button
                onClick={loadEntries}
                style={{
                  padding: "6px 14px",
                  borderRadius: 8,
                  border: "none",
                  background: "#dc2626",
                  color: "#ffffff",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Retry
              </button>
            </div>
          ) : filteredEntries.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "48px 24px",
                background: "var(--card-bg)",
                borderRadius: 18,
                border: "1px dashed var(--border)",
              }}
            >
              <div style={{ marginBottom: 12, opacity: 0.5 }}>
                <Sparkles size={48} />
              </div>
              <h3 style={{ margin: "0 0 6px 0", fontSize: "1.15rem", fontWeight: 700, color: "var(--text-h)" }}>
                No memories recorded yet
              </h3>
              <p style={{ margin: "0 auto 18px", maxWidth: 420, color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Start building your trip chronicle! Add your thoughts, favorite moments, reflections, and photos from your journey.
              </p>
              <button
                onClick={handleOpenNewEditor}
                style={{
                  background: "var(--accent)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 12,
                  padding: "8px 18px",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Plus size={16} /> Add First Memory
              </button>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
              {filteredEntries.map((entry) => {
                const isAuthor = entry.author_id === currentUserId;
                const isOwner = userRole === "owner";
                const canEdit = isAuthor;
                const canDelete = isAuthor || isOwner;

                const dateStr = entry.created_at
                  ? new Date(entry.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "";

                return (
                  <div
                    key={entry.id}
                    style={{
                      background: "var(--card-bg)",
                      borderRadius: 18,
                      padding: "24px",
                      border: "1px solid var(--border)",
                      boxShadow: "var(--card-shadow, 0 4px 16px rgba(0,0,0,0.03))",
                      transition: "all 0.2s ease",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        flexWrap: "wrap",
                        gap: 10,
                        marginBottom: 12,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: "50%",
                            background: entry.is_private ? "rgba(124, 58, 237, 0.15)" : "rgba(2, 132, 199, 0.15)",
                            color: entry.is_private ? "#8b5cf6" : "var(--accent)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 700,
                            fontSize: "0.9rem",
                          }}
                        >
                          {(entry.author_name || entry.author_id).slice(0, 2).toUpperCase()}
                        </div>

                        <div>
                          <div style={{ fontWeight: 600, fontSize: "0.92rem", color: "var(--text-h)" }}>
                            {entry.author_name || entry.author_id}
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>{dateStr}</div>
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {entry.day_number && (
                          <span
                            style={{
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              padding: "3px 8px",
                              borderRadius: 8,
                              background: "var(--bg-alt)",
                              color: "var(--text-muted)",
                              border: "1px solid var(--border)",
                            }}
                          >
                            Day {entry.day_number}
                          </span>
                        )}

                        {entry.attraction_name && (
                          <span
                            style={{
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              padding: "3px 8px",
                              borderRadius: 8,
                              background: "rgba(79, 70, 229, 0.1)",
                              color: "var(--accent)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                            }}
                          >
                            <MapPin size={12} /> {entry.attraction_name}
                          </span>
                        )}

                        <span
                          style={{
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            padding: "3px 8px",
                            borderRadius: 8,
                            background: entry.is_private ? "rgba(124, 58, 237, 0.15)" : "rgba(16, 185, 129, 0.15)",
                            color: entry.is_private ? "#8b5cf6" : "#10b981",
                            border: entry.is_private ? "1px solid rgba(124, 58, 237, 0.3)" : "1px solid rgba(16, 185, 129, 0.3)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          {entry.is_private ? <Lock size={10} /> : <Users size={10} />}
                          {entry.is_private ? "Private" : "Shared"}
                        </span>

                        {canEdit && (
                          <button
                            onClick={() => handleOpenEditEditor(entry)}
                            title="Edit entry"
                            style={{
                              background: "transparent",
                              border: "none",
                              cursor: "pointer",
                              color: "var(--text-muted)",
                              padding: 4,
                              display: "flex",
                              alignItems: "center",
                            }}
                          >
                            <Edit3 size={15} />
                          </button>
                        )}

                        {canDelete && (
                          <button
                            onClick={() => handleDelete(entry.id)}
                            disabled={deletingId === entry.id}
                            title="Delete entry"
                            style={{
                              background: "transparent",
                              border: "none",
                              cursor: "pointer",
                              color: "#ef4444",
                              padding: 4,
                              display: "flex",
                              alignItems: "center",
                            }}
                          >
                            <Trash2 size={15} />
                          </button>
                        )}
                      </div>
                    </div>

                    {entry.title && (
                      <h4
                        style={{
                          margin: "0 0 10px 0",
                          fontSize: "1.1rem",
                          fontWeight: 700,
                          color: "var(--text-h)",
                        }}
                      >
                        {entry.title}
                      </h4>
                    )}

                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                      <p
                        style={{
                          margin: 0,
                          color: "var(--text)",
                          fontSize: "0.95rem",
                          lineHeight: 1.6,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {entry.content}
                      </p>

                      {entry.photo_url && (
                        <div style={{ marginTop: 6 }}>
                          <img
                            src={getAuthenticatedPhotoSrc(entry.photo_url)}
                            alt={entry.title || "Travel memory photo"}
                            onClick={() => setLightboxPhoto(entry.photo_url!)}
                            style={{
                              maxHeight: 280,
                              maxWidth: "100%",
                              borderRadius: 14,
                              objectFit: "cover",
                              cursor: "pointer",
                              border: "1px solid var(--border)",
                              boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
                              transition: "transform 0.2s ease",
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.01)")}
                            onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                          />
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4, display: "flex", alignItems: "center", gap: 4 }}>
                            <Search size={12} /> Click photo to enlarge
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
