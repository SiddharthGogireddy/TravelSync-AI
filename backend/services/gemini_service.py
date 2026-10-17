import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional, Union
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("travelsync.gemini")

# Validated model configuration with documented default compatible with current Google GenAI API
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
SUPPORTED_GEMINI_MODELS = {
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
}


def get_configured_model() -> str:
    """Returns the validated model identifier from GEMINI_MODEL, defaulting to gemini-3.8-flash."""
    configured = (os.getenv("GEMINI_MODEL") or "").strip()
    if configured:
        clean = configured.removeprefix("models/")
        if clean in SUPPORTED_GEMINI_MODELS:
            return clean
        logger.warning(
            "Configured GEMINI_MODEL '%s' is unrecognized. Supported models: %s. Falling back to '%s'.",
            configured,
            ", ".join(sorted(SUPPORTED_GEMINI_MODELS)),
            DEFAULT_GEMINI_MODEL,
        )
    return DEFAULT_GEMINI_MODEL


# Internal client cache
_client = None


def get_client():
    """Lazily initializes and returns the Google GenAI client without failing at import time."""
    global _client
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return None

    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.warning("Failed to initialize Google GenAI client: %s", e)
            return None
    return _client


# Backward-compatible client reference
class _ClientProxy:
    @property
    def models(self):
        c = get_client()
        if c is not None:
            return c.models
        raise RuntimeError("Google GenAI client is uninitialized. Ensure GEMINI_API_KEY is configured.")


client = _ClientProxy()


def is_quota_error(exc: Exception) -> bool:
    """Determines if an exception corresponds to HTTP 429 quota exhaustion."""
    err_str = str(exc)
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status_code in (429, "429"):
        return True
    if any(k in err_str for k in ("429", "RESOURCE_EXHAUSTED", "Quota exceeded", "quotaMetric")):
        return True
    return False


def is_non_retryable_error(exc: Exception) -> bool:
    """Determines if an error should NOT be retried (4xx errors, quota exhaustion, not found)."""
    if is_quota_error(exc):
        return True
    err_str = str(exc)
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status_code in (400, 401, 403, 404, "400", "401", "403", "404"):
        return True
    if any(k in err_str for k in ("NOT_FOUND", "INVALID_ARGUMENT", "PERMISSION_DENIED", "UNAUTHENTICATED", "API_KEY_INVALID", "API_KEY")):
        return True
    return False


def _clean_json_text(raw_text: str) -> str:
    """Strips markdown code fences and whitespace from LLM output."""
    text = (raw_text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _extract_json_payload(text: str) -> Optional[Union[Dict[str, Any], list]]:
    """Attempts direct json parsing, falling back to substring object/array extraction."""
    cleaned = _clean_json_text(text)
    if not cleaned:
        return None

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first matching JSON object or array substring
    match_obj = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match_obj:
        try:
            return json.loads(match_obj.group(1))
        except json.JSONDecodeError:
            pass

    match_arr = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    if match_arr:
        try:
            return json.loads(match_arr.group(1))
        except json.JSONDecodeError:
            pass

    return None


def generate(prompt: str, max_retries: int = 2) -> Optional[Any]:
    """
    Executes a content generation request using the configured Gemini model.

    Reliability semantics:
    - If GEMINI_API_KEY is not configured, logs a single warning and returns None.
    - If HTTP 429 / RESOURCE_EXHAUSTED occurs, logs quota notice and returns None immediately without retrying.
    - Non-retryable 4xx client errors (e.g. model not found, invalid argument) fail fast without looping.
    - If transient network or server errors (timeouts, 5xx) occur, performs bounded retries with exponential backoff.
    - Cleans markdown fences and parses JSON safely, returning None on unparseable outputs.
    - Never prints or discloses secrets.
    """
    if not prompt or not str(prompt).strip():
        return None

    gen_client = get_client()
    if gen_client is None:
        logger.info("GEMINI_API_KEY is not configured; AI dynamic generation skipped.")
        return None

    model_name = get_configured_model()
    attempts = 0

    while attempts <= max_retries:
        try:
            response = gen_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )

            text = getattr(response, "text", "") or ""
            if not text:
                return None

            parsed = _extract_json_payload(text)
            if parsed is not None:
                return parsed

            # If prompt did not request JSON or output is non-JSON text, return raw text
            return text.strip()

        except Exception as e:
            if is_quota_error(e):
                logger.warning(
                    "Gemini API quota exhausted (HTTP 429 RESOURCE_EXHAUSTED) for model '%s'. "
                    "Skipping retries to preserve provider limits. AI generation temporarily unavailable.",
                    model_name,
                )
                return None

            if is_non_retryable_error(e):
                logger.warning(
                    "Non-retryable client error calling Gemini model '%s': %s. Skipping retries.",
                    model_name,
                    e,
                )
                return None

            attempts += 1
            if attempts <= max_retries:
                backoff_delay = 0.5 * (2 ** (attempts - 1))
                logger.warning(
                    "Transient error calling Gemini model '%s' (attempt %d/%d): %s. Retrying in %.1fs...",
                    model_name,
                    attempts,
                    max_retries,
                    e,
                    backoff_delay,
                )
                time.sleep(backoff_delay)
            else:
                logger.error(
                    "Gemini API call failed after %d attempts for model '%s': %s",
                    max_retries + 1,
                    model_name,
                    e,
                )
                return None

    return None


def get_gemini_service_status() -> Dict[str, Any]:
    """Returns non-sensitive operational status of the Gemini service."""
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    return {
        "configured": bool(api_key),
        "model": get_configured_model(),
        "default_model": DEFAULT_GEMINI_MODEL,
        "supported_models": sorted(list(SUPPORTED_GEMINI_MODELS)),
    }
       