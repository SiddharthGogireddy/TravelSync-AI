"""
Unit and integration tests for Step 73: Live Currency Conversion.
Validates cross-rate conversion arithmetic, rounding, invalid currencies,
provider timeouts and fallbacks, in-memory caching, non-mutation of saved data,
and frontend currency service integration.
"""

import os
import sys
import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip
from backend.services.currency.currency_service import (
    convert_currency_amount,
    calculate_cross_rates,
    validate_currency_code,
    get_live_exchange_rates,
    clear_currency_cache,
    FALLBACK_RATES_USD,
    SUPPORTED_CURRENCIES,
)

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BASE_DIR / "frontend" / "src"


@pytest.fixture(autouse=True)
def reset_currency_cache():
    clear_currency_cache()
    yield
    clear_currency_cache()


def test_currency_conversion_arithmetic_same_base():
    """Verify conversion arithmetic when rates share base USD."""
    rates = {
        "USD": 1.0,
        "INR": 83.5,
        "EUR": 0.92,
        "GBP": 0.80,
    }

    # 100 USD -> INR
    assert convert_currency_amount(100, "USD", "INR", rates) == 8350.0
    # 100 USD -> EUR
    assert convert_currency_amount(100, "USD", "EUR", rates) == 92.0
    # 100 USD -> GBP
    assert convert_currency_amount(100, "USD", "GBP", rates) == 80.0


def test_cross_rate_conversion_and_inverse():
    """Verify cross-rate conversion (INR -> EUR) and inverse accuracy."""
    rates = {
        "USD": 1.0,
        "INR": 83.5,
        "EUR": 0.92,
    }

    # 8350 INR -> EUR should be approx 92 EUR (8350 * 0.92 / 83.5 = 92)
    eur_amt = convert_currency_amount(8350, "INR", "EUR", rates)
    assert eur_amt == 92.0

    # Inverse conversion: 92 EUR -> INR
    inr_amt = convert_currency_amount(eur_amt, "EUR", "INR", rates)
    assert inr_amt == 8350.0


def test_identical_source_and_target_currency_preserves_amount():
    """Verify converting to the same currency returns exact amount without modification."""
    rates = {"INR": 83.5, "USD": 1.0}
    assert convert_currency_amount(12500, "INR", "INR", rates) == 12500.0
    assert convert_currency_amount(99.99, "USD", "USD", rates) == 99.99


def test_invalid_currency_code_validation():
    """Verify invalid or malformed currency codes raise validation errors."""
    with pytest.raises(ValueError, match="Invalid currency code"):
        validate_currency_code("TOOLONG")

    with pytest.raises(ValueError, match="Invalid currency code"):
        validate_currency_code("12")

    with pytest.raises(ValueError, match="non-empty string"):
        validate_currency_code("")

    rates = {"USD": 1.0, "INR": 83.5}
    with pytest.raises(ValueError, match="unavailable"):
        convert_currency_amount(100, "XYZ", "USD", rates)


def test_rounding_precision():
    """Verify converted amounts round cleanly to 2 decimal places."""
    rates = {"USD": 1.0, "EUR": 0.9166666}
    converted = convert_currency_amount(100, "USD", "EUR", rates)
    assert converted == 91.67
    assert isinstance(converted, float)


def test_supported_currencies_endpoint():
    """Verify GET /currency/supported returns curated currency list and metadata."""
    res = client.get("/currency/supported")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "INR" in data["currencies"]
    assert "USD" in data["currencies"]
    assert "EUR" in data["currencies"]
    assert data["currencies"]["INR"]["symbol"] == "₹"
    assert data["currencies"]["USD"]["symbol"] == "$"


def test_live_rates_endpoint_and_caching():
    """Verify rates endpoint retrieves rates and caches subsequent calls."""
    res1 = client.get("/currency/rates?base=USD")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["base"] == "USD"
    assert "INR" in data1["rates"]
    assert "EUR" in data1["rates"]
    assert "timestamp" in data1
    assert "disclaimer" in data1

    # Second call should be served from in-memory cache
    res2 = client.get("/currency/rates?base=USD")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_cached"] is True
    assert data2["rates"] == data1["rates"]


def test_provider_failure_and_resilient_fallback():
    """Verify service gracefully falls back to baseline rates on external network timeout."""
    import httpx
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Network timed out")):
        res = client.get("/currency/rates?base=USD")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["is_fallback"] is True
        assert data["base"] == "USD"
        assert data["rates"]["INR"] == FALLBACK_RATES_USD["INR"]
        assert "disclaimer" in data


def test_convert_endpoint():
    """Verify GET /currency/convert performs accurate live conversion."""
    res = client.get("/currency/convert?amount=10000&source=INR&target=USD")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["original_amount"] == 10000
    assert data["source_currency"] == "INR"
    assert data["target_currency"] == "USD"
    assert data["converted_amount"] > 0
    assert data["exchange_rate"] > 0
    assert "disclaimer" in data


def test_convert_endpoint_rejects_negative_amounts():
    """Verify negative conversion amounts return HTTP 400."""
    res = client.get("/currency/convert?amount=-50&source=INR&target=USD")
    assert res.status_code == 400
    assert "negative" in res.json()["detail"].lower()


def test_preservation_of_original_trip_budget_amounts():
    """Verify currency conversion in UI/API never mutates saved trip data in storage."""
    raw_trip = {
        "trip": {
            "source": "Delhi",
            "destination": "Goa",
            "days": 2,
            "budget": {
                "total_budget": 25000,
                "estimated_cost": 18500,
                "remaining": 6500,
                "currency": "INR",
            },
        }
    }
    trip_id = save_trip(raw_trip)

    # Perform conversions
    conv_res = client.get("/currency/convert?amount=25000&source=INR&target=EUR")
    assert conv_res.status_code == 200

    # Reload saved trip from store
    reloaded = load_trip(trip_id)
    inner = reloaded.get("trip", reloaded)
    assert inner["budget"]["total_budget"] == 25000
    assert inner["budget"]["estimated_cost"] == 18500
    assert inner["budget"]["currency"] == "INR"


# ============================================================================
# FRONTEND SOURCE & COMPONENT VERIFICATION
# ============================================================================

def test_frontend_currency_service():
    """Verify frontend/src/services/currency.ts exports convertCurrency, formatCurrency, getExchangeRates."""
    curr_service = FRONTEND_SRC / "services" / "currency.ts"
    assert curr_service.exists(), "currency.ts must exist"
    content = curr_service.read_text(encoding="utf-8")

    assert "convertCurrency" in content
    assert "formatCurrency" in content
    assert "getExchangeRates" in content
    assert "getSupportedCurrencies" in content
    assert "Intl.NumberFormat" in content


def test_frontend_currency_selector_component():
    """Verify frontend/src/components/CurrencySelector.tsx implements accessible dropdown and status."""
    selector_file = FRONTEND_SRC / "components" / "CurrencySelector.tsx"
    assert selector_file.exists(), "CurrencySelector.tsx must exist"
    content = selector_file.read_text(encoding="utf-8")

    assert "CurrencySelector" in content
    assert "currency-select" in content
    assert "aria-label=" in content
    assert "onCurrencyChange" in content
    assert "selectedCurrency" in content


def test_frontend_budget_card_supports_display_currency():
    """Verify BudgetCard.tsx displays converted amount and original source currency indicator."""
    card_file = FRONTEND_SRC / "components" / "BudgetCard.tsx"
    content = card_file.read_text(encoding="utf-8")

    assert "displayCurrency" in content
    assert "originalCurrency" in content
    assert "formatAmount" in content
    assert "Orig:" in content
    assert "Indicative exchange rate conversion" in content


def test_frontend_trip_view_integrates_currency_selector():
    """Verify TripView.tsx integrates CurrencySelector in budget section."""
    tv_file = FRONTEND_SRC / "pages" / "TripView.tsx"
    content = tv_file.read_text(encoding="utf-8")

    assert "CurrencySelector" in content
    assert "selectedCurrency" in content
    assert "ratesData" in content
    assert "formatTripAmount" in content
    assert "section-budget" in content
