"""Centralized FastAPI exception handlers and error formatting for TravelSync AI."""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.services.error.redaction import redact_sensitive_text, sanitize_for_client

logger = logging.getLogger("travelsync.errors")

STATUS_CODE_MAP: Dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}

DEFAULT_USER_MESSAGES: Dict[int, str] = {
    400: "Invalid request parameters or payload.",
    401: "Authentication credentials are missing or invalid.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    409: "A resource conflict occurred. Please refresh and try again.",
    413: "The uploaded payload exceeds the allowable size limit.",
    422: "Validation failed for the submitted data.",
    429: "Too many requests. Please slow down and try again shortly.",
    500: "An unexpected server error occurred. Please try again later.",
    502: "External service is currently unreachable.",
    503: "The service is temporarily unavailable. Please try again shortly.",
    504: "The request timed out. Please try again.",
}


def build_error_payload(
    status_code: int,
    detail: Any,
    error_code: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build standardized error response dictionary."""
    resolved_code = error_code or STATUS_CODE_MAP.get(status_code, "ERROR")

    # Determine safe user-facing message
    if message:
        safe_message = message
    elif isinstance(detail, str) and detail.strip() and len(detail) <= 300:
        safe_message = sanitize_for_client(detail)
    else:
        safe_message = DEFAULT_USER_MESSAGES.get(
            status_code, "An error occurred while processing the request."
        )

    # Sanitize detail if string
    clean_detail = sanitize_for_client(detail) if isinstance(detail, str) else detail

    return {
        "error_code": resolved_code,
        "message": safe_message,
        "detail": clean_detail,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def http_exception_handler(
    request: Request, exc: Union[StarletteHTTPException, Exception]
) -> JSONResponse:
    """Handle standard HTTPException instances while preserving status and headers."""
    status_code = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", "An error occurred")
    headers = getattr(exc, "headers", None)

    payload = build_error_payload(
        status_code=status_code,
        detail=detail,
    )

    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request schema validation errors (422) with structured field errors."""
    raw_errors = exc.errors()

    formatted_details: List[Dict[str, Any]] = []
    for err in raw_errors:
        loc = err.get("loc", ())
        field_name = ".".join(str(item) for item in loc if item != "body")
        formatted_details.append(
            {
                "field": field_name or "request",
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
        )

    payload = build_error_payload(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=jsonable_encoder(raw_errors),  # Preserves raw errors list for backwards compatibility with tests
        error_code="VALIDATION_ERROR",
        message="Validation failed for the submitted data.",
        details=formatted_details,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload,
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle application ValueError as HTTP 400 Bad Request."""
    err_msg = str(exc) or "Invalid value provided."
    payload = build_error_payload(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=err_msg,
        error_code="BAD_REQUEST",
        message=err_msg,
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=payload,
    )


async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    """Handle application KeyError as HTTP 404 Not Found."""
    clean_key = str(exc).strip("'\"")
    err_msg = f"Resource or field '{clean_key}' was not found."
    payload = build_error_payload(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=err_msg,
        error_code="NOT_FOUND",
        message=err_msg,
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=payload,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled unexpected exceptions, log redacted diagnostic context, and return safe 500."""
    client_host = request.client.host if request.client else "unknown"
    safe_url = redact_sensitive_text(str(request.url))
    raw_tb = traceback.format_exc()
    redacted_tb = redact_sensitive_text(raw_tb)

    logger.error(
        "Unhandled server exception on %s %s (client=%s): %s\n%s",
        request.method,
        safe_url,
        client_host,
        redact_sensitive_text(str(exc)),
        redacted_tb,
    )

    payload = build_error_payload(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected server error occurred. Please try again later.",
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers on the FastAPI application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(KeyError, key_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
