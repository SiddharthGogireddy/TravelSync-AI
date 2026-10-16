import React, { useState, useEffect, useRef, useId } from "react";
import {
  MapPin,
  Plane,
  Train,
  Landmark,
  Palmtree,
  Building2,
  Home,
  Trees,
  Check,
  AlertTriangle,
  X,
  Search,
} from "lucide-react";
import { searchLocations } from "../services/api";
import type { LocationSuggestion } from "../types/trip";

export interface LocationAutocompleteProps {
  id?: string;
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string, suggestion?: LocationSuggestion) => void;
  onClear?: () => void;
  isValid?: boolean;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  helperText?: string;
  className?: string;
  inputStyle?: React.CSSProperties;
}

/**
 * Format a LocationSuggestion into a clean, readable display label.
 */
export function formatLocationLabel(suggestion: LocationSuggestion): string {
  const parts: string[] = [];
  if (suggestion.name) {
    parts.push(suggestion.name.trim());
  }
  if (suggestion.region && suggestion.region !== suggestion.name) {
    parts.push(suggestion.region.trim());
  }
  if (
    suggestion.country &&
    suggestion.country !== suggestion.name &&
    suggestion.country !== suggestion.region
  ) {
    parts.push(suggestion.country.trim());
  }

  if (parts.length > 0) {
    return parts.join(", ");
  }
  return suggestion.display_name || suggestion.name || "Unknown Location";
}

function getPlaceIcon(category?: string, type?: string) {
  const c = (category || "").toLowerCase();
  const t = (type || "").toLowerCase();

  if (t.includes("aerodrome") || t.includes("airport") || c.includes("airport")) {
    return <Plane size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  if (t.includes("station") || t.includes("railway") || c.includes("railway")) {
    return <Train size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  if (c.includes("tourism") || c.includes("historic") || t.includes("monument") || t.includes("museum")) {
    return <Landmark size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  if (c.includes("water") || t.includes("beach") || t.includes("lake") || t.includes("sea")) {
    return <Palmtree size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  if (t.includes("city") || t.includes("administrative") || t.includes("town") || t.includes("municipality")) {
    return <Building2 size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  if (t.includes("village") || t.includes("hamlet") || t.includes("suburb")) {
    return <Home size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  if (c.includes("natural") || t.includes("peak") || t.includes("mountain") || t.includes("park")) {
    return <Trees size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
  }
  return <MapPin size={15} style={{ color: "var(--accent)", flexShrink: 0 }} />;
}

export const LocationAutocomplete: React.FC<LocationAutocompleteProps> = ({
  id: propId,
  label,
  placeholder = "Search worldwide cities, airports, landmarks...",
  value,
  onChange,
  onClear,
  isValid = false,
  required = false,
  disabled = false,
  error,
  helperText,
  className = "",
  inputStyle,
}) => {
  const generatedId = useId();
  const inputId = propId || `loc-ac-${generatedId}`;
  const listboxId = `${inputId}-listbox`;

  const [query, setQuery] = useState(value);
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [touched, setTouched] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync internal query text when value prop changes externally
  useEffect(() => {
    setQuery(value);
  }, [value]);

  // Handle outside click to close dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Cleanup abort controller and debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  const triggerSearch = (searchQuery: string) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const trimmed = searchQuery.trim();
    if (trimmed.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      setIsLoading(false);
      setFetchError(null);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    debounceTimerRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const results = await searchLocations(trimmed, 6, controller.signal);
        setSuggestions(results);
        setIsOpen(true);
        setHighlightedIndex(-1);
      } catch (err: any) {
        if (err.name === "AbortError") {
          return; // Ignore aborted requests
        }
        setFetchError(
          err?.status === 429
            ? "Too many requests. Please wait a moment."
            : "Unable to reach geocoding service. Please check connection."
        );
        setSuggestions([]);
        setIsOpen(true);
      } finally {
        setIsLoading(false);
      }
    }, 350);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVal = e.target.value;
    setQuery(newVal);
    setTouched(true);
    // Any keystroke invalidates previous selection until a suggestion is picked
    onChange(newVal, undefined);
    triggerSearch(newVal);
  };

  const handleSelectSuggestion = (suggestion: LocationSuggestion) => {
    const formatted = formatLocationLabel(suggestion);
    setQuery(formatted);
    setSuggestions([]);
    setIsOpen(false);
    setHighlightedIndex(-1);
    setFetchError(null);
    setTouched(true);
    onChange(formatted, suggestion);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleClear = () => {
    setQuery("");
    setSuggestions([]);
    setIsOpen(false);
    setHighlightedIndex(-1);
    setFetchError(null);
    if (onClear) {
      onClear();
    } else {
      onChange("", undefined);
    }
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen && suggestions.length > 0) {
        setIsOpen(true);
        setHighlightedIndex(0);
        return;
      }
      if (suggestions.length > 0) {
        setHighlightedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (suggestions.length > 0) {
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
      }
    } else if (e.key === "Enter") {
      if (isOpen && highlightedIndex >= 0 && suggestions[highlightedIndex]) {
        e.preventDefault();
        handleSelectSuggestion(suggestions[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
      setHighlightedIndex(-1);
    }
  };

  const showUnverifiedWarning = touched && query.trim().length > 0 && !isValid && !isOpen && !isLoading;

  return (
    <div
      ref={containerRef}
      className={`location-autocomplete-container ${className}`}
      style={{ position: "relative", width: "100%", boxSizing: "border-box" }}
    >
      {label && (
        <label
          htmlFor={inputId}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontWeight: 600,
            fontSize: "0.92rem",
            marginBottom: "4px",
            color: "var(--text-h, #1e293b)",
          }}
        >
          <span>
            {label} {required && <span style={{ color: "#ef4444" }}>*</span>}
          </span>
          {isValid && query.trim().length > 0 && (
            <span
              style={{
                fontSize: "0.75rem",
                color: "#10b981",
                background: "rgba(16, 185, 129, 0.12)",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                padding: "2px 8px",
                borderRadius: "9999px",
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <Check size={12} strokeWidth={2.5} />
              Verified
            </span>
          )}
        </label>
      )}

      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-activedescendant={
            highlightedIndex >= 0 ? `${listboxId}-opt-${highlightedIndex}` : undefined
          }
          aria-invalid={Boolean(error || showUnverifiedWarning)}
          disabled={disabled}
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0 && !isOpen) {
              setIsOpen(true);
            }
          }}
          style={{
            width: "100%",
            paddingRight: query ? "64px" : "36px",
            borderColor: error
              ? "#ef4444"
              : showUnverifiedWarning
              ? "#f59e0b"
              : isValid
              ? "#10b981"
              : undefined,
            ...inputStyle,
          }}
        />

        {/* Right action icons (Loading spinner, Clear button) */}
        <div
          style={{
            position: "absolute",
            right: "10px",
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          {isLoading && (
            <div
              title="Searching locations..."
              style={{
                width: "14px",
                height: "14px",
                border: "2px solid var(--border)",
                borderTopColor: "var(--accent)",
                borderRadius: "50%",
                animation: "spin 0.6s linear infinite",
              }}
            />
          )}

          {query && !disabled && (
            <button
              type="button"
              onClick={handleClear}
              aria-label="Clear location input"
              title="Clear location"
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "4px",
                color: "var(--text-muted)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "4px",
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Inline Unverified or Error hint */}
      {showUnverifiedWarning && (
        <div
          style={{
            fontSize: "0.8rem",
            color: "#d97706",
            marginTop: "4px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <AlertTriangle size={14} style={{ color: "#d97706", flexShrink: 0 }} />
          <span>Please select a verified location from the suggestions dropdown.</span>
        </div>
      )}

      {error && (
        <div style={{ fontSize: "0.8rem", color: "#dc2626", marginTop: "4px" }}>
          {error}
        </div>
      )}

      {helperText && !error && !showUnverifiedWarning && (
        <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "4px" }}>
          {helperText}
        </div>
      )}

      {/* Autocomplete Dropdown Listbox */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            zIndex: 1050,
            background: "var(--dropdown-bg)",
            color: "var(--text-h)",
            border: "1px solid var(--dropdown-border)",
            borderRadius: "8px",
            boxShadow: "var(--shadow-lg)",
            maxHeight: "280px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {fetchError ? (
            <div style={{ padding: "14px 16px", textAlign: "center" }}>
              <p style={{ color: "#dc2626", fontSize: "0.88rem", margin: "0 0 8px 0" }}>
                {fetchError}
              </p>
              <button
                type="button"
                onClick={() => triggerSearch(query)}
                style={{
                  padding: "4px 12px",
                  fontSize: "0.8rem",
                  background: "var(--accent-bg)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent-border)",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Retry
              </button>
            </div>
          ) : suggestions.length > 0 ? (
            suggestions.map((suggestion, idx) => {
              const isHighlighted = highlightedIndex === idx;
              const icon = getPlaceIcon(suggestion.category, suggestion.type);
              const secondaryText = [suggestion.region, suggestion.country]
                .filter(Boolean)
                .join(", ");

              return (
                <div
                  key={suggestion.place_id || `${suggestion.latitude}-${suggestion.longitude}-${idx}`}
                  id={`${listboxId}-opt-${idx}`}
                  role="option"
                  aria-selected={isHighlighted}
                  onMouseEnter={() => setHighlightedIndex(idx)}
                  onClick={() => handleSelectSuggestion(suggestion)}
                  style={{
                    padding: "10px 14px",
                    cursor: "pointer",
                    borderBottom: "1px solid var(--border)",
                    background: isHighlighted ? "var(--dropdown-hover)" : "transparent",
                    transition: "background 0.1s ease",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "10px",
                  }}
                >
                  <span style={{ display: "inline-flex", alignItems: "center", marginTop: "3px" }}>
                    {icon}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: "0.92rem",
                        color: isHighlighted ? "var(--accent)" : "var(--text-h)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {suggestion.name}
                    </div>
                    <div
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        marginTop: "2px",
                      }}
                    >
                      {secondaryText || suggestion.display_name}
                    </div>
                  </div>
                  {suggestion.type && (
                    <span
                      style={{
                        fontSize: "0.72rem",
                        color: "var(--text-muted)",
                        background: "var(--code-bg)",
                        border: "1px solid var(--border)",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        textTransform: "capitalize",
                        alignSelf: "center",
                      }}
                    >
                      {suggestion.type.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
              );
            })
          ) : !isLoading && query.trim().length >= 2 ? (
            <div style={{ padding: "16px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.88rem" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 500 }}>
                <Search size={16} style={{ color: "var(--text-muted)" }} />
                <span>No matching locations found for &ldquo;{query}&rdquo;.</span>
              </div>
              <p style={{ margin: "4px 0 0 0", fontSize: "0.78rem", color: "var(--text-muted)" }}>
                Try searching by city, state, or country name.
              </p>
            </div>
          ) : null}

          {/* OpenStreetMap / Nominatim Attribution Footer */}
          <div
            style={{
              padding: "6px 12px",
              background: "var(--code-bg)",
              borderTop: "1px solid var(--dropdown-border)",
              fontSize: "0.72rem",
              color: "var(--text-muted)",
              textAlign: "right",
              borderRadius: "0 0 8px 8px",
            }}
          >
            Location data ©{" "}
            <a
              href="https://www.openstreetmap.org/copyright"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent)", textDecoration: "underline" }}
            >
              OpenStreetMap contributors
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
