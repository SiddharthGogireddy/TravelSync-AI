import { API } from "./api";

export interface CurrencyInfo {
  name: string;
  symbol: string;
}

export interface SupportedCurrenciesResponse {
  success: boolean;
  currencies: Record<string, CurrencyInfo>;
  default: string;
}

export interface ExchangeRatesResponse {
  success: boolean;
  base: string;
  rates: Record<string, number>;
  timestamp?: string;
  is_cached?: boolean;
  is_fallback?: boolean;
  is_stale?: boolean;
  provider?: string;
  disclaimer?: string;
}

// In-memory frontend cache to prevent re-fetching across component renders
let _cachedRates: ExchangeRatesResponse | null = null;
let _cachedRatesPromise: Promise<ExchangeRatesResponse> | null = null;

export async function getSupportedCurrencies(): Promise<SupportedCurrenciesResponse> {
  const res = await fetch(`${API}/currency/supported`);
  if (!res.ok) {
    throw new Error(`Failed to load supported currencies (${res.status})`);
  }
  return res.json();
}

export async function getExchangeRates(base: string = "USD", forceRefresh = false): Promise<ExchangeRatesResponse> {
  if (!forceRefresh && _cachedRates && _cachedRates.base === base) {
    return _cachedRates;
  }
  if (!forceRefresh && _cachedRatesPromise) {
    return _cachedRatesPromise;
  }

  _cachedRatesPromise = (async () => {
    try {
      const res = await fetch(`${API}/currency/rates?base=${encodeURIComponent(base)}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch exchange rates (${res.status})`);
      }
      const data: ExchangeRatesResponse = await res.json();
      _cachedRates = data;
      return data;
    } finally {
      _cachedRatesPromise = null;
    }
  })();

  return _cachedRatesPromise;
}

/**
 * Converts an amount from source currency to target currency using a shared base rate table.
 * Formula: amount * (target_rate / source_rate)
 */
export function convertCurrency(
  amount: number,
  sourceCurrency: string = "INR",
  targetCurrency: string = "INR",
  rates?: Record<string, number> | null
): number {
  if (typeof amount !== "number" || isNaN(amount)) {
    return 0;
  }
  const src = (sourceCurrency || "INR").trim().toUpperCase();
  const tgt = (targetCurrency || "INR").trim().toUpperCase();

  if (src === tgt || !rates) {
    return amount;
  }

  const srcRate = rates[src];
  const tgtRate = rates[tgt];

  if (!srcRate || !tgtRate || srcRate <= 0 || tgtRate <= 0) {
    // If rate is missing for either currency, avoid corrupting the number
    return amount;
  }

  const converted = amount * (tgtRate / srcRate);
  return Math.round(converted * 100) / 100;
}

/**
 * Formats a currency amount with locale-aware symbol and separator formatting.
 * Safely falls back if the currency code is unrecognized.
 */
export function formatCurrency(
  amount: number,
  currencyCode: string = "INR",
  locale?: string
): string {
  const code = (currencyCode || "INR").trim().toUpperCase();
  const safeAmount = typeof amount === "number" && !isNaN(amount) ? amount : 0;

  try {
    const fractionDigits = Math.abs(safeAmount) >= 100 ? 0 : 2;
    return new Intl.NumberFormat(locale || undefined, {
      style: "currency",
      currency: code,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(safeAmount);
  } catch (err) {
    // Fallback for non-standard or unsupported currency codes
    return `${code} ${Math.round(safeAmount).toLocaleString()}`;
  }
}
