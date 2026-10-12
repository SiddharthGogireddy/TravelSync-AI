import type { CurrencyInfo } from "../services/currency";

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
  supportedCurrencies = DEFAULT_CURRENCIES,
  rateTimestamp,
  isCached,
  isFallback,
  isStale,
  loading,
  error,
}: CurrencySelectorProps) {
  const currencies = supportedCurrencies || DEFAULT_CURRENCIES;

  return (
    <div
      className="currency-selector-container"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        background: "#f8fafc",
        padding: "6px 12px",
        borderRadius: 10,
        border: "1px solid #e2e8f0",
        boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
      }}
    >
      <label
        htmlFor="currency-select"
        style={{
          fontSize: "0.82rem",
          fontWeight: 600,
          color: "#475569",
          display: "flex",
          alignItems: "center",
          gap: 5,
          cursor: "pointer",
        }}
      >
        <span aria-hidden="true">💱</span>
        <span>Display Currency:</span>
      </label>

      <select
        id="currency-select"
        value={selectedCurrency}
        onChange={(e) => onCurrencyChange(e.target.value)}
        aria-label="Select display currency"
        style={{
          background: "#ffffff",
          border: "1px solid #cbd5e1",
          borderRadius: 6,
          padding: "4px 10px",
          fontSize: "0.85rem",
          fontWeight: 600,
          color: "#0f172a",
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
          color: error ? "#b91c1c" : isFallback ? "#b45309" : "#64748b",
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {loading ? (
          <span style={{ color: "#3b82f6" }}>Updating rates...</span>
        ) : error ? (
          <span title={error}>⚠️ Offline rates</span>
        ) : isFallback ? (
          <span title="Rates estimated from TravelSync baseline">⚡ Baseline rates</span>
        ) : isStale ? (
          <span title={`Cached rates from ${rateTimestamp || "recent update"}`}>🕒 Cached</span>
        ) : (
          <span title={`Live rates updated: ${rateTimestamp || "recent"}`}>
            ● {isCached ? "Cached" : "Live"}
          </span>
        )}
      </div>
    </div>
  );
}
