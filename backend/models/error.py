"""Standard API error response models for TravelSync AI."""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized API error response payload.

    Provides a stable error_code, user-friendly message, and preserves
    'detail' for full backwards compatibility with existing clients and tests.
    """

    error_code: str = Field(
        ...,
        description="Stable machine-readable error code (e.g. NOT_FOUND, VALIDATION_ERROR)",
    )
    message: str = Field(
        ...,
        description="Safe, user-facing error message",
    )
    detail: Any = Field(
        ...,
        description="Detailed error information or string (backwards compatible)",
    )
    details: Optional[Any] = Field(
        default=None,
        description="Optional structured validation or contextual error details",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp when the error occurred",
    )
