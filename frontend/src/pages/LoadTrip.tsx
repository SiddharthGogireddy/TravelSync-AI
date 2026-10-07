import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { getTrip, importTrip } from "../services/api";

export default function LoadTrip() {
  const [tripId, setTripId] = useState("");
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(false);

  const [importJsonText, setImportJsonText] = useState("");
  const [importError, setImportError] = useState("");
  const [importSuccess, setImportSuccess] = useState("");
  const [importing, setImporting] = useState(false);

  const navigate = useNavigate();

  // Load existing trip by ID
  const handleLoadTrip = async () => {
    if (!tripId.trim()) {
      setLoadError("Please enter a Trip ID");
      return;
    }

    try {
      setLoadError("");
      setLoading(true);
      await getTrip(tripId.trim());
      navigate(`/trip/${tripId.trim()}`);
    } catch {
      setLoadError("Trip not found");
    } finally {
      setLoading(false);
    }
  };

  // Import trip from parsed object
  const processTripImport = async (data: unknown) => {
    setImportError("");
    setImportSuccess("");
    setImporting(true);

    try {
      if (!data || typeof data !== "object") {
        throw new Error("Invalid format: imported file must be a JSON object");
      }

      const res = await importTrip(data);
      setImportSuccess(`Trip restored successfully! ID: ${res.trip_id}`);
      setTimeout(() => {
        navigate(`/trip/${res.trip_id}`);
      }, 600);
    } catch (err: any) {
      setImportError(err.message || "Failed to import trip");
    } finally {
      setImporting(false);
    }
  };

  // Handle JSON file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        await processTripImport(parsed);
      } catch (err: any) {
        setImportError(
          err instanceof SyntaxError
            ? "Malformed JSON file: unable to parse syntax"
            : err.message || "Failed to read file"
        );
      }
    };
    reader.onerror = () => {
      setImportError("Failed to read the selected file");
    };
    reader.readAsText(file);
    // Reset file input so the same file can be re-selected if desired
    e.target.value = "";
  };

  // Handle JSON pasted in textarea
  const handleTextImport = async () => {
    if (!importJsonText.trim()) {
      setImportError("Please paste a JSON trip payload");
      return;
    }

    try {
      const parsed = JSON.parse(importJsonText.trim());
      await processTripImport(parsed);
    } catch (err: any) {
      setImportError(
        err instanceof SyntaxError
          ? "Malformed JSON: please check the syntax and try again"
          : err.message || "Failed to import JSON"
      );
    }
  };

  return (
    <div
      style={{
        maxWidth: 720,
        margin: "40px auto",
        padding: "0 20px",
        textAlign: "left",
      }}
    >
      <div style={{ marginBottom: 20 }}>
        <Link
          to="/"
          style={{
            color: "#6366f1",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          &larr; Back to Planner
        </Link>
      </div>

      <h1 style={{ textAlign: "left", marginBottom: 8 }}>
        Load &amp; Restore Trip
      </h1>
      <p style={{ color: "#6b7280", marginBottom: 30 }}>
        Open an existing trip by ID or restore a trip from an exported JSON file.
      </p>

      {/* Section 1: Load by ID */}
      <div
        style={{
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          padding: 24,
          marginBottom: 30,
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: 8, fontSize: "1.2rem" }}>
          Load Trip by ID
        </h3>
        <p style={{ color: "#6b7280", fontSize: "0.9rem", marginBottom: 16 }}>
          Enter the unique Trip ID you saved or received from a shared trip link.
        </p>

        <div style={{ display: "flex", gap: 10 }}>
          <input
            type="text"
            placeholder="e.g. 58f53f24-0282-4595-9200-feea26be569f"
            value={tripId}
            onChange={(e) => setTripId(e.target.value)}
            style={{
              flex: 1,
              marginTop: 0,
              padding: "10px 14px",
              borderRadius: 8,
              border: "1px solid #d1d5db",
            }}
          />
          <button
            onClick={handleLoadTrip}
            disabled={loading}
            style={{
              padding: "10px 20px",
              background: "#4f46e5",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            {loading ? "Loading..." : "Load Trip"}
          </button>
        </div>

        {loadError && (
          <p
            style={{
              color: "#dc2626",
              marginTop: 10,
              fontSize: "0.9rem",
              fontWeight: 500,
            }}
          >
            {loadError}
          </p>
        )}
      </div>

      {/* Section 2: Import from JSON File or Text */}
      <div
        style={{
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          padding: 24,
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: 8, fontSize: "1.2rem" }}>
          Import Trip from JSON
        </h3>
        <p style={{ color: "#6b7280", fontSize: "0.9rem", marginBottom: 16 }}>
          Restore a trip from a previously exported TravelSync AI JSON file. A new unique Trip ID will be assigned so your existing trips stay safe.
        </p>

        {/* File upload option */}
        <div
          style={{
            border: "2px dashed #c7d2fe",
            background: "#f5f7ff",
            borderRadius: 10,
            padding: 24,
            textAlign: "center",
            marginBottom: 20,
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: 8, color: "#374151" }}>
            Upload Exported JSON File
          </p>
          <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: 16 }}>
            Select any valid TravelSync AI export file (.json)
          </p>
          <label
            style={{
              display: "inline-block",
              padding: "10px 22px",
              background: "#4f46e5",
              color: "#fff",
              borderRadius: 8,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Choose JSON File
            <input
              type="file"
              accept=".json,application/json"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
          </label>
        </div>

        {/* Paste JSON text option */}
        <div>
          <label
            style={{
              display: "block",
              fontWeight: 600,
              fontSize: "0.9rem",
              color: "#374151",
              marginBottom: 6,
            }}
          >
            Or paste JSON payload directly:
          </label>
          <textarea
            rows={5}
            placeholder='Paste JSON here, e.g. {"version": "1.0", "trip": {...}}'
            value={importJsonText}
            onChange={(e) => setImportJsonText(e.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "10px 14px",
              borderRadius: 8,
              border: "1px solid #d1d5db",
              fontFamily: "ui-monospace, monospace",
              fontSize: "0.85rem",
              marginBottom: 10,
            }}
          />
          <button
            onClick={handleTextImport}
            disabled={importing}
            style={{
              padding: "10px 20px",
              background: "#10b981",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            {importing ? "Importing..." : "Restore Trip from JSON"}
          </button>
        </div>

        {importError && (
          <p
            style={{
              color: "#dc2626",
              marginTop: 14,
              fontSize: "0.9rem",
              fontWeight: 500,
              background: "#fee2e2",
              padding: "8px 12px",
              borderRadius: 6,
            }}
          >
            {importError}
          </p>
        )}

        {importSuccess && (
          <p
            style={{
              color: "#065f46",
              marginTop: 14,
              fontSize: "0.9rem",
              fontWeight: 600,
              background: "#d1fae5",
              padding: "8px 12px",
              borderRadius: 6,
            }}
          >
            {importSuccess}
          </p>
        )}
      </div>
    </div>
  );
}