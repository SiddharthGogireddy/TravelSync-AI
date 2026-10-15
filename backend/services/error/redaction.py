"""Redaction utilities for safe diagnostic logging and client error sanitation."""

import re
from typing import Any

# Patterns to identify sensitive strings
_JWT_PATTERN = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9-_+/=]*)?"
)
_BEARER_PATTERN = re.compile(
    r"Bearer\s+[A-Za-z0-9-_\.]+",
    re.IGNORECASE,
)
_SECRET_QUOTED_PATTERN = re.compile(
    r'(?i)(["\']?(?:password|secret|access_token|refresh_token|api_key|token|auth)["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])'
)
_SECRET_UNQUOTED_PATTERN = re.compile(
    r'(?i)(\b(?:password|secret|access_token|refresh_token|api_key|token|auth)\s*[:=]\s*)([^\s,;&"\']+)'
)
_WINDOWS_PATH_PATTERN = re.compile(
    r"[a-zA-Z]:\\[\\\S]+",
)


def redact_sensitive_text(text: str) -> str:
    """Redact sensitive tokens, passwords, and credentials from text for safe logging."""
    if not isinstance(text, str):
        return text

    # Redact Bearer tokens first
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    # Redact any standalone JWTs
    redacted = _JWT_PATTERN.sub("[REDACTED_JWT]", redacted)
    # Redact quoted password / secret key-value pairs
    redacted = _SECRET_QUOTED_PATTERN.sub(r"\1[REDACTED]\3", redacted)
    # Redact unquoted password / secret key-value pairs
    redacted = _SECRET_UNQUOTED_PATTERN.sub(r"\1[REDACTED]", redacted)
    return redacted


def sanitize_for_client(text: str) -> str:
    """Sanitize internal errors before sending to clients, stripping internal paths."""
    if not isinstance(text, str):
        return text
    clean = redact_sensitive_text(text)
    # Strip local Windows/Linux path prefixes to prevent directory structure exposure
    clean = _WINDOWS_PATH_PATTERN.sub("[internal_path]", clean)
    return clean
