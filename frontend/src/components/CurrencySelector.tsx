import type { CurrencyInfo } from "../services/currency";
import { Coins, AlertTriangle, Clock } from "lucide-react";

interface CurrencySelectorProps {
  selectedCurrency: string;
  onCurrencyChange: (currency: string) => void;
  supportedCurrencies?: Record<string, CurrencyInfo>;
  rateTimestamp?: string;
  isCached?: boolean;
  isFallback?: boolean;
  isStale?: boolean;
  loading?: boolean;
  error?: string | null;
}

const DEFAULT_CURRENCIES: Record<string, CurrencyInfo> = {
  INR: { name: "Indian Rupee", symbol: "₹" },
  USD: { name: "US Dollar", symbol: "$" },
  EUR: { name: "Euro", symbol: "€" },
  GBP: { name: "British Pound", symbol: "£" },
  JPY: { name: "Japanese Yen", symbol: "¥" },
  AED: { name: "UAE Dirham", symbol: "AED" },
  AUD: { name: "Australian Dollar", symbol: "A$" },
  CAD: { name: "Canadian Dollar", symbol: "C$" },
  SGD: { name: "Singapore Dollar", symbol: "S$" },
  CHF: { name: "Swiss Franc", symbol: "CHF" },
  THB: { name: "Thai Baht", symbol: "฿" },
  MYR: { name: "Malaysian Ringgit", symbol: "RM" },
};

export default function CurrencySelector({
  selectedCurrency,
  onCurrencyChange,
  supportedCurrencies,
  rateTimestamp,
  isCached,
  isFallback,
  isStale,
  loading,
  error,
}: CurrencySelectorProps) {
  const currencies = supportedCurrencies && Object.keys(supportedCurrencies).length > 0
    ? supportedCurrencies
    : DEFAULT_CURRENCIES;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        background: "var(--code-bg)",
        padding: "6px 12px",
        borderRadius: 10,
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow)",
      }}
    >
      <label
        htmlFor="currency-select"
        style={{
          fontSize: "0.82rem",
          fontWeight: 600,
          color: "var(--input-label)",
          display: "flex",
          alignItems: "center",
          gap: 6,
          cursor: "pointer",
        }}
      >
        <Coins size={14} style={{ color: "var(--accent)" }} />
        <span>Display Currency:</span>
      </label>

      <select
        id="currency-select"
        value={selectedCurrency}
        onChange={(e) => onCurrencyChange(e.target.value)}
        aria-label="Select display currency"
        style={{
          background: "var(--input-bg)",
          border: "1px solid var(--input-border)",
          borderRadius: 6,
          padding: "4px 10px",
          fontSize: "0.85rem",
          fontWeight: 600,
          color: "var(--input-text)",
          cursor: "pointer",
          outline: "none",
        }}
      >
        {Object.entries(currencies).map(([code, info]) => (
          <option key={code} value={code}>
            {code} ({info.symbol}) — {info.name}
          </option>
        ))}
      </select>

      {/* Status indicator */}
      <div
        style={{
          fontSize: "0.74rem",
          color: error ? "#ef4444" : isFallback ? "#f59e0b" : "var(--text-muted)",
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {loading ? (
          <span style={{ color: "var(--accent)" }}>Updating rates...</span>
        ) : error ? (
          <span title={error} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <AlertTriangle size={12} /> Offline rates
          </span>
        ) : isFallback ? (
          <span title="Rates estimated from TravelSync baseline">Baseline rates</span>
        ) : isStale ? (
          <span title={`Cached rates from ${rateTimestamp || "recent update"}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Clock size={12} /> Cached
          </span>
        ) : (
          <span title={`Live rates updated: ${rateTimestamp || "recent"}`}>
            ● {isCached ? "Cached" : "Live"}
          </span>
        )}
      </div>
    </div>
  );
}
