"""
TravelSync AI - Live Currency Exchange & Conversion Service
Integrates open exchange-rate API with configurable timeouts, caching,
deterministic cross-rate conversion arithmetic, and resilient fallbacks.
"""

import time
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Primary free, keyless exchange rate provider
PROVIDER_URL = "https://open.er-api.com/v6/latest/{base}"
PROVIDER_TIMEOUT_SECONDS = 6.0
CACHE_TTL_SECONDS = 3600.0  # 1 hour in-memory TTL

# Curated supported currencies with human-friendly metadata
SUPPORTED_CURRENCIES: Dict[str, Dict[str, str]] = {
    "INR": {"name": "Indian Rupee", "symbol": "₹"},
    "USD": {"name": "US Dollar", "symbol": "$"},
    "EUR": {"name": "Euro", "symbol": "€"},
    "GBP": {"name": "British Pound", "symbol": "£"},
    "JPY": {"name": "Japanese Yen", "symbol": "¥"},
    "AED": {"name": "UAE Dirham", "symbol": "AED"},
    "AUD": {"name": "Australian Dollar", "symbol": "A$"},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$"},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$"},
    "CHF": {"name": "Swiss Franc", "symbol": "CHF"},
    "THB": {"name": "Thai Baht", "symbol": "฿"},
    "MYR": {"name": "Malaysian Ringgit", "symbol": "RM"},
    "NZD": {"name": "New Zealand Dollar", "symbol": "NZ$"},
    "CNY": {"name": "Chinese Yuan", "symbol": "¥"},
    "BRL": {"name": "Brazilian Real", "symbol": "R$"},
}

# Reliable baseline exchange rates (relative to USD = 1.0) for fallback/offline scenarios
FALLBACK_RATES_USD: Dict[str, float] = {
    "USD": 1.0,
    "INR": 83.50,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 155.0,
    "AED": 3.67,
    "AUD": 1.52,
    "CAD": 1.36,
    "SGD": 1.35,
    "CHF": 0.90,
    "THB": 36.50,
    "MYR": 4.70,
    "NZD": 1.65,
    "CNY": 7.23,
    "BRL": 5.15,
}

# In-memory rate cache
_EXCHANGE_CACHE: Dict[str, Any] = {
    "base": None,
    "rates": {},
    "timestamp": None,
    "cached_at": 0.0,
    "provider": "open.er-api.com",
}


def clear_currency_cache() -> None:
    """Clears the in-memory rate cache (useful for testing)."""
    _EXCHANGE_CACHE["base"] = None
    _EXCHANGE_CACHE["rates"] = {}
    _EXCHANGE_CACHE["timestamp"] = None
    _EXCHANGE_CACHE["cached_at"] = 0.0


def validate_currency_code(code: str) -> str:
    """Validates that a currency code is a 3-letter ISO-4217 string."""
    if not code or not isinstance(code, str):
        raise ValueError("Currency code must be a non-empty string.")
    cleaned = code.strip().upper()
    if not re.match(r"^[A-Z]{3}$", cleaned):
        raise ValueError(f"Invalid currency code format: '{code}'. Must be a 3-letter ISO code.")
    return cleaned


def calculate_cross_rates(base: str, usd_rates: Dict[str, float]) -> Dict[str, float]:
    """
    Computes exchange rates for any requested base from a set of USD-denominated rates.
    If base is USD, returns usd_rates directly.
    Otherwise: rate(CUR) = usd_rates[CUR] / usd_rates[base].
    """
    if base == "USD":
        return dict(usd_rates)

    base_in_usd = usd_rates.get(base)
    if not base_in_usd or base_in_usd <= 0:
        raise ValueError(f"Base currency '{base}' not found in rate table.")

    converted_rates: Dict[str, float] = {}
    for cur, rate in usd_rates.items():
        if rate > 0:
            converted_rates[cur] = round(rate / base_in_usd, 6)
    converted_rates[base] = 1.0
    return converted_rates


def convert_currency_amount(
    amount: float,
    source_currency: str,
    target_currency: str,
    rates: Dict[str, float],
) -> float:
    """
    Converts amount from source_currency to target_currency using exchange rates sharing the same base.
    Formula: amount * (target_rate / source_rate).
    """
    try:
        amt = float(amount)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid conversion amount: '{amount}'. Must be a numeric value.")

    src = validate_currency_code(source_currency)
    tgt = validate_currency_code(target_currency)

    if src == tgt:
        return round(amt, 2)

    src_rate = rates.get(src)
    tgt_rate = rates.get(tgt)

    if not src_rate or src_rate <= 0:
        raise ValueError(f"Exchange rate for source currency '{src}' is unavailable.")
    if not tgt_rate or tgt_rate <= 0:
        raise ValueError(f"Exchange rate for target currency '{tgt}' is unavailable.")

    # Cross-rate conversion
    converted = amt * (tgt_rate / src_rate)
    return round(converted, 2)


async def get_live_exchange_rates(base: str = "USD") -> Dict[str, Any]:
    """
    Retrieves exchange rates for the given base currency.
    Uses in-memory cache if fresh, otherwise fetches from open.er-api.com.
    Falls back gracefully to cached/fallback rates on provider error or timeout.
    """
    clean_base = validate_currency_code(base)
    now_ts = time.time()

    # 1. Check cache
    if (
        _EXCHANGE_CACHE.get("rates")
        and _EXCHANGE_CACHE.get("base") == clean_base
        and (now_ts - _EXCHANGE_CACHE.get("cached_at", 0)) < CACHE_TTL_SECONDS
    ):
        return {
            "success": True,
            "base": clean_base,
            "rates": dict(_EXCHANGE_CACHE["rates"]),
            "timestamp": _EXCHANGE_CACHE.get("timestamp"),
            "is_cached": True,
            "is_fallback": False,
            "provider": _EXCHANGE_CACHE.get("provider"),
            "disclaimer": "Exchange rates are indicative estimates for informational planning and may not reflect real-time payment provider or bank transaction rates.",
        }

    # 2. Attempt fetching from provider
    fetch_url = PROVIDER_URL.format(base=clean_base)
    try:
        async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT_SECONDS) as http_client:
            resp = await http_client.get(fetch_url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("result") == "success" and isinstance(data.get("rates"), dict):
                    raw_rates = data["rates"]
                    # Ensure positive numeric rates
                    valid_rates = {k.upper(): float(v) for k, v in raw_rates.items() if isinstance(v, (int, float)) and v > 0}
                    rate_time = data.get("time_last_update_utc") or datetime.now(timezone.utc).isoformat()

                    # Update cache
                    _EXCHANGE_CACHE["base"] = clean_base
                    _EXCHANGE_CACHE["rates"] = valid_rates
                    _EXCHANGE_CACHE["timestamp"] = rate_time
                    _EXCHANGE_CACHE["cached_at"] = now_ts

                    return {
                        "success": True,
                        "base": clean_base,
                        "rates": valid_rates,
                        "timestamp": rate_time,
                        "is_cached": False,
                        "is_fallback": False,
                        "provider": "open.er-api.com",
                        "disclaimer": "Exchange rates are indicative estimates for informational planning and may not reflect real-time payment provider or bank transaction rates.",
                    }
    except Exception as e:
        logger.warning(f"Failed to fetch live exchange rates from {fetch_url}: {e}")

    # 3. Fallback: If cached rates for clean_base exist (even if expired), return stale cache
    if _EXCHANGE_CACHE.get("rates") and _EXCHANGE_CACHE.get("base") == clean_base:
        return {
            "success": True,
            "base": clean_base,
            "rates": dict(_EXCHANGE_CACHE["rates"]),
            "timestamp": _EXCHANGE_CACHE.get("timestamp"),
            "is_cached": True,
            "is_fallback": False,
            "is_stale": True,
            "provider": _EXCHANGE_CACHE.get("provider"),
            "disclaimer": "Exchange rates are indicative estimates for informational planning and may not reflect real-time payment provider or bank transaction rates.",
        }

    # 4. Fallback: Compute rates from known static table
    fallback_rates = calculate_cross_rates(clean_base, FALLBACK_RATES_USD)
    return {
        "success": True,
        "base": clean_base,
        "rates": fallback_rates,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "is_cached": False,
        "is_fallback": True,
        "provider": "TravelSync Baseline Rates",
        "disclaimer": "Exchange rates are indicative estimates for informational planning and may not reflect real-time payment provider or bank transaction rates.",
    }
