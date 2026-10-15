"""CORS configuration parser and origin validator for TravelSync AI."""

import os
from typing import List


DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def parse_cors_origins() -> List[str]:
    """
    Parses and validates allowed CORS origins from ALLOWED_ORIGINS environment variable.

    Security Rules:
    1. In production (AUTH_DEV_MODE=false):
       - ALLOWED_ORIGINS is mandatory and cannot be empty.
       - Wildcard '*' is strictly prohibited when allow_credentials=True.
       - Raises RuntimeError on missing or invalid origin configuration.
    2. In development (AUTH_DEV_MODE=true):
       - If ALLOWED_ORIGINS is not set, falls back to safe local dev origins (Vite, local ports).
       - Explicit dev ALLOWED_ORIGINS are parsed and respected.
    """
    dev_mode = os.getenv("AUTH_DEV_MODE", "true").lower() in ("true", "1", "yes")
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")

    origins = [item.strip() for item in raw_origins.split(",") if item.strip()]

    if origins:
        if "*" in origins and not dev_mode:
            raise RuntimeError(
                "Fatal configuration error: Wildcard '*' in ALLOWED_ORIGINS is not permitted with credentialed requests in production mode."
            )
        return origins

    if dev_mode:
        return list(DEFAULT_DEV_ORIGINS)

    raise RuntimeError(
        "Fatal configuration error: ALLOWED_ORIGINS environment variable is required in production mode."
    )
