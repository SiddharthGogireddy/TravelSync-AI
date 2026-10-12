import React, { useState, useEffect } from "react";
import {
  MONTH_NAMES,
  DAY_NAMES,
  getDaysInMonth,
  getFirstDayOfWeek,
  formatDateString,
  parseDateString,
  calculateDaysBetween,
  isDateInRange,
  getTodayString,
  formatDisplayDate,
} from "../utils/dateUtils";

export interface TravelDatePickerProps {
  startDate: string;
  endDate: string;
  onChange: (startDate: string, endDate: string, durationDays: number) => void;
  maxTripDurationDays?: number;
}

export const TravelDatePicker: React.FC<TravelDatePickerProps> = ({
  startDate,
  endDate,
  onChange,
  maxTripDurationDays = 30,
}) => {
  const todayStr = getTodayString();
  const parsedToday = parseDateString(todayStr)!;

  // Initialize view month/year from startDate, or today
  const initialDate = parseDateString(startDate) || parsedToday;
  const [viewYear, setViewYear] = useState<number>(initialDate.year);
  const [viewMonth, setViewMonth] = useState<number>(initialDate.month); // 1-12
  const [validationError, setValidationError] = useState<string>("");

  // Sync view if startDate changes externally
  useEffect(() => {
    if (startDate) {
      const parsed = parseDateString(startDate);
      if (parsed) {
        setViewYear(parsed.year);
        setViewMonth(parsed.month);
      }
    }
  }, [startDate]);

  const handlePrevMonth = () => {
    if (viewMonth === 1) {
      setViewMonth(12);
      setViewYear((prev) => prev - 1);
    } else {
      setViewMonth((prev) => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (viewMonth === 12) {
      setViewMonth(1);
      setViewYear((prev) => prev + 1);
    } else {
      setViewMonth((prev) => prev + 1);
    }
  };

  const handleMonthSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setViewMonth(parseInt(e.target.value, 10));
  };

  const handleYearSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setViewYear(parseInt(e.target.value, 10));
  };

  const handleDateClick = (clickedDateStr: string) => {
    setValidationError("");

    // If no start date, or both start & end dates are already chosen, start a fresh range
    if (!startDate || (startDate && endDate)) {
      onChange(clickedDateStr, "", 1);
      return;
    }

    // Only start date is chosen; now selecting end date
    if (clickedDateStr < startDate) {
      // User clicked an earlier date: treat as new start date
      onChange(clickedDateStr, "", 1);
      return;
    }

    const duration = calculateDaysBetween(startDate, clickedDateStr);
    if (duration > maxTripDurationDays) {
      setValidationError(`Maximum trip duration is ${maxTripDurationDays} days. Selected range is ${duration} days.`);
      return;
    }

    onChange(startDate, clickedDateStr, duration);
  };

  const handleClear = () => {
    setValidationError("");
    onChange("", "", 0);
  };

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstDayOfWeek = getFirstDayOfWeek(viewYear, viewMonth);

  // Available year range: current year - 1 to current year + 6
  const currentYear = parsedToday.year;
  const availableYears = Array.from({ length: 8 }, (_, i) => currentYear - 1 + i);

  // Compute duration label
  const durationDays = startDate && endDate ? calculateDaysBetween(startDate, endDate) : 0;

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
        padding: "16px",
        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04)",
        maxWidth: "420px",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      {/* Month Navigation & Selector Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
          gap: "8px",
        }}
      >
        <button
          type="button"
          onClick={handlePrevMonth}
          aria-label="Previous month"
          style={{
            padding: "6px 12px",
            borderRadius: "6px",
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            color: "#334155",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: "0.95rem",
          }}
        >
          &larr;
        </button>

        {/* Quick Month & Year Dropdowns */}
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <select
            value={viewMonth}
            onChange={handleMonthSelect}
            aria-label="Select month"
            style={{
              padding: "6px 8px",
              borderRadius: "6px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#1e293b",
              fontWeight: 600,
              fontSize: "0.88rem",
              cursor: "pointer",
            }}
          >
            {MONTH_NAMES.map((name, idx) => (
              <option key={name} value={idx + 1}>
                {name}
              </option>
            ))}
          </select>

          <select
            value={viewYear}
            onChange={handleYearSelect}
            aria-label="Select year"
            style={{
              padding: "6px 8px",
              borderRadius: "6px",
              border: "1px solid #cbd5e1",
              background: "#ffffff",
              color: "#1e293b",
              fontWeight: 600,
              fontSize: "0.88rem",
              cursor: "pointer",
            }}
          >
            {availableYears.map((yr) => (
              <option key={yr} value={yr}>
                {yr}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={handleNextMonth}
          aria-label="Next month"
          style={{
            padding: "6px 12px",
            borderRadius: "6px",
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            color: "#334155",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: "0.95rem",
          }}
        >
          &rarr;
        </button>
      </div>

      {/* Weekday Heading */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: "2px",
          textAlign: "center",
          fontWeight: 700,
          fontSize: "0.76rem",
          color: "#64748b",
          marginBottom: "6px",
        }}
      >
        {DAY_NAMES.map((d) => (
          <div key={d} style={{ padding: "4px 0" }}>
            {d}
          </div>
        ))}
      </div>

      {/* Calendar Days Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: "4px",
        }}
      >
        {/* Blank offset cells for starting day */}
        {Array.from({ length: firstDayOfWeek }).map((_, i) => (
          <div key={`blank-${i}`} style={{ height: "36px" }} />
        ))}

        {/* Days of the month */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const dayNum = i + 1;
          const dateStr = formatDateString(viewYear, viewMonth, dayNum);
          const isStart = dateStr === startDate;
          const isEnd = dateStr === endDate;
          const inRange = startDate && endDate && isDateInRange(dateStr, startDate, endDate);
          const isToday = dateStr === todayStr;

          // Check if selecting as end date would exceed 30 days
          const wouldExceedMax =
            startDate && !endDate && dateStr > startDate && calculateDaysBetween(startDate, dateStr) > maxTripDurationDays;

          let bg = "transparent";
          let textColor = "#1e293b";
          let fontWeight: number | string = 500;
          let borderRadius = "6px";
          let border = "1px solid transparent";

          if (isStart || isEnd) {
            bg = "#4f46e5";
            textColor = "#ffffff";
            fontWeight = 700;
          } else if (inRange) {
            bg = "#e0e7ff";
            textColor = "#3730a3";
            fontWeight = 600;
          } else if (wouldExceedMax) {
            textColor = "#cbd5e1";
          }

          if (isToday && !isStart && !isEnd) {
            border = "1px solid #6366f1";
            fontWeight = 700;
          }

          return (
            <button
              type="button"
              key={dateStr}
              onClick={() => handleDateClick(dateStr)}
              disabled={Boolean(wouldExceedMax)}
              title={
                wouldExceedMax
                  ? `Trip cannot exceed ${maxTripDurationDays} days`
                  : isToday
                  ? "Today"
                  : dateStr
              }
              aria-label={`Select ${dateStr}`}
              style={{
                height: "36px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: bg,
                color: textColor,
                border: border,
                borderRadius: borderRadius,
                fontSize: "0.85rem",
                fontWeight: fontWeight,
                cursor: wouldExceedMax ? "not-allowed" : "pointer",
                position: "relative",
                transition: "all 0.15s ease",
              }}
            >
              {dayNum}
              {isToday && !isStart && !isEnd && (
                <span
                  style={{
                    position: "absolute",
                    bottom: "2px",
                    width: "4px",
                    height: "4px",
                    borderRadius: "50%",
                    background: "#6366f1",
                  }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Validation / error message banner */}
      {validationError && (
        <div
          style={{
            marginTop: "10px",
            padding: "8px 12px",
            borderRadius: "6px",
            background: "#fee2e2",
            color: "#b91c1c",
            fontSize: "0.82rem",
            fontWeight: 600,
          }}
        >
          {validationError}
        </div>
      )}

      {/* Selection Summary Footer */}
      <div
        style={{
          marginTop: "14px",
          paddingTop: "12px",
          borderTop: "1px solid #f1f5f9",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ fontSize: "0.85rem", color: "#475569" }}>
          {startDate ? (
            <span>
              <strong>{formatDisplayDate(startDate)}</strong>
              {endDate ? (
                <>
                  {" "}
                  &rarr; <strong>{formatDisplayDate(endDate)}</strong>{" "}
                  <span
                    style={{
                      background: "#e0e7ff",
                      color: "#3730a3",
                      padding: "2px 8px",
                      borderRadius: "12px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      marginLeft: "4px",
                    }}
                  >
                    {durationDays} {durationDays === 1 ? "Day" : "Days"}
                  </span>
                </>
              ) : (
                <span style={{ color: "#6366f1", fontStyle: "italic" }}> (Pick return date)</span>
              )}
            </span>
          ) : (
            <span style={{ color: "#94a3b8" }}>Select departure date</span>
          )}
        </div>

        {(startDate || endDate) && (
          <button
            type="button"
            onClick={handleClear}
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              border: "none",
              background: "#f1f5f9",
              color: "#64748b",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
};

export default TravelDatePicker;
