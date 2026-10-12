/**
 * Pure timezone-safe date utilities for TravelSync AI calendar and date selection.
 * Operates purely on year, month, and day integers to prevent timezone-induced off-by-one shifts.
 */

export const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
] as const;

export const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

/**
 * Determines whether a given year is a leap year.
 */
export function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

/**
 * Returns the exact number of days in a given month (month is 1-indexed: 1 = Jan, 12 = Dec).
 * Properly handles 28, 29, 30, and 31 day months, including leap-year February.
 */
export function getDaysInMonth(year: number, month: number): number {
  if (month < 1 || month > 12) {
    throw new Error(`Invalid month: ${month}. Month must be between 1 and 12.`);
  }
  if (month === 2) {
    return isLeapYear(year) ? 29 : 28;
  }
  if (month === 4 || month === 6 || month === 9 || month === 11) {
    return 30;
  }
  return 31;
}

/**
 * Returns the weekday index (0 = Sun, 1 = Mon, ..., 6 = Sat) of the first day of the month.
 */
export function getFirstDayOfWeek(year: number, month: number): number {
  return new Date(year, month - 1, 1).getDay();
}

/**
 * Formats year, month (1-12), and day into an ISO YYYY-MM-DD date string.
 */
export function formatDateString(year: number, month: number, day: number): string {
  const y = String(year).padStart(4, "0");
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Parses a YYYY-MM-DD string into year, month (1-12), and day numbers.
 */
export function parseDateString(dateStr: string): { year: number; month: number; day: number } | null {
  if (!dateStr || typeof dateStr !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr.trim());
  if (!match) return null;
  const year = parseInt(match[1], 10);
  const month = parseInt(match[2], 10);
  const day = parseInt(match[3], 10);
  if (month < 1 || month > 12) return null;
  const maxDays = getDaysInMonth(year, month);
  if (day < 1 || day > maxDays) return null;
  return { year, month, day };
}

/**
 * Computes the inclusive number of days between two YYYY-MM-DD date strings.
 * E.g., 2026-10-15 to 2026-10-15 is 1 day; 2026-10-15 to 2026-10-17 is 3 days.
 * Returns negative if endDate < startDate.
 */
export function calculateDaysBetween(startDateStr: string, endDateStr: string): number {
  const start = parseDateString(startDateStr);
  const end = parseDateString(endDateStr);
  if (!start || !end) return 0;
  const utcStart = Date.UTC(start.year, start.month - 1, start.day);
  const utcEnd = Date.UTC(end.year, end.month - 1, end.day);
  const diffDays = Math.round((utcEnd - utcStart) / (1000 * 60 * 60 * 24));
  return diffDays + 1;
}

/**
 * Returns true if dateStrA is strictly before dateStrB.
 */
export function isDateBefore(dateStrA: string, dateStrB: string): boolean {
  return dateStrA < dateStrB;
}

/**
 * Returns true if dateStrA is strictly after dateStrB.
 */
export function isDateAfter(dateStrA: string, dateStrB: string): boolean {
  return dateStrA > dateStrB;
}

/**
 * Returns true if dateStr falls inclusively within [startDateStr, endDateStr].
 */
export function isDateInRange(dateStr: string, startDateStr: string, endDateStr: string): boolean {
  if (!startDateStr || !endDateStr) return false;
  return dateStr >= startDateStr && dateStr <= endDateStr;
}

/**
 * Returns today's date formatted as YYYY-MM-DD.
 */
export function getTodayString(): string {
  const now = new Date();
  return formatDateString(now.getFullYear(), now.getMonth() + 1, now.getDate());
}

/**
 * Formats a YYYY-MM-DD string into a user-friendly label (e.g., "Oct 15, 2026").
 */
export function formatDisplayDate(dateStr: string): string {
  const parsed = parseDateString(dateStr);
  if (!parsed) return dateStr;
  const monthAbbr = MONTH_NAMES[parsed.month - 1].slice(0, 3);
  return `${monthAbbr} ${parsed.day}, ${parsed.year}`;
}
