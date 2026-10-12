"""
FastAPI Router for Live Currency Exchange and Conversion
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

from backend.services.currency.currency_service import (
    SUPPORTED_CURRENCIES,
    get_live_exchange_rates,
    convert_currency_amount,
    validate_currency_code,
)

router = APIRouter(
    prefix="/currency",
    tags=["Currency"],
)


@router.get("/supported")
def get_supported_currencies() -> Dict[str, Any]:
    """
    Returns curated list of supported world currencies with names and symbols.
    """
    return {
        "success": True,
        "currencies": SUPPORTED_CURRENCIES,
        "default": "INR",
    }


@router.get("/rates")
async def get_rates(
    base: str = Query(default="USD", description="3-letter ISO base currency code, e.g. USD, INR, EUR")
) -> Dict[str, Any]:
    """
    Returns exchange rates relative to the requested base currency.
    Includes rate timestamp and cache indicators.
    """
    try:
        clean_base = validate_currency_code(base)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    rates_data = await get_live_exchange_rates(base=clean_base)
    return rates_data


@router.get("/convert")
async def convert_price(
    amount: float = Query(..., description="Amount to convert"),
    source: str = Query(default="INR", description="Source currency ISO code"),
    target: str = Query(default="USD", description="Target currency ISO code"),
) -> Dict[str, Any]:
    """
    Converts amount from source currency to target currency using current exchange rates.
    """
    try:
        clean_source = validate_currency_code(source)
        clean_target = validate_currency_code(target)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if amount < 0:
        raise HTTPException(status_code=400, detail="Amount cannot be negative.")

    # Retrieve rates with clean_source as base for highest precision
    rates_data = await get_live_exchange_rates(base=clean_source)
    rates = rates_data.get("rates", {})

    try:
        converted = convert_currency_amount(amount, clean_source, clean_target, rates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    rate = rates.get(clean_target, 1.0)

    return {
        "success": True,
        "original_amount": amount,
        "source_currency": clean_source,
        "target_currency": clean_target,
        "converted_amount": converted,
        "exchange_rate": rate,
        "timestamp": rates_data.get("timestamp"),
        "is_cached": rates_data.get("is_cached", False),
        "is_fallback": rates_data.get("is_fallback", False),
        "disclaimer": rates_data.get("disclaimer"),
    }
