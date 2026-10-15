import collections
import logging
import os
import re
import threading
import time
from typing import Dict, Deque, Optional, Tuple, NamedTuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitRule(NamedTuple):
    pattern: re.Pattern
    limit: int
    window_seconds: int
    name: str


class SlidingWindowRateLimiter:
    """
    Thread-safe, high-performance in-memory sliding window rate limiter.
    Stores timestamps in deques and purges entries older than the window duration.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Mapping: (rule_name, client_identifier) -> Deque[float] of hit timestamps
        self._hits: Dict[Tuple[str, str], Deque[float]] = collections.defaultdict(collections.deque)
        self._last_cleanup = time.time()

    def is_allowed(
        self,
        key: str,
        rule_name: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Determines if a request is allowed under the sliding window limit.

        Returns:
            (allowed: bool, remaining: int, retry_after: int)
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Periodic cleanup of completely stale entries every 60 seconds
            if now - self._last_cleanup > 60:
                self._cleanup_stale(now)
                self._last_cleanup = now

            queue = self._hits[(rule_name, key)]

            # Pop older timestamps outside the current sliding window
            while queue and queue[0] < cutoff:
                queue.popleft()

            current_count = len(queue)
            if current_count >= limit:
                # Calculate remaining seconds until oldest request expires
                oldest_timestamp = queue[0]
                retry_after = max(1, int(oldest_timestamp + window_seconds - now) + 1)
                return False, 0, retry_after

            # Record this hit
            queue.append(now)
            remaining = max(0, limit - (current_count + 1))
            return True, remaining, 0

    def _cleanup_stale(self, now: float):
        """Purges queues that have had zero activity for more than 10 minutes."""
        stale_threshold = now - 600
        keys_to_delete = []
        for k, queue in self._hits.items():
            while queue and queue[0] < stale_threshold:
                queue.popleft()
            if not queue:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            del self._hits[k]

    def reset(self):
        """Clears all tracking queues (used in testing)."""
        with self._lock:
            self._hits.clear()


# Global limiter instance
global_limiter = SlidingWindowRateLimiter()

# Configured endpoint rules
DEFAULT_RULES = [
    # 1. Planner & Heavy LLM Generation: 5 req/min
    RateLimitRule(
        pattern=re.compile(r"^/planner(?:/.*)?$"),
        limit=int(os.getenv("RATELIMIT_PLANNER_LIMIT", "5")),
        window_seconds=int(os.getenv("RATELIMIT_PLANNER_WINDOW", "60")),
        name="planner_generation",
    ),
    # 2. Trip Optimization & Assistant Chat: 10 req/min
    RateLimitRule(
        pattern=re.compile(r"^/trip/[^/]+/(?:optimize-trip|assistant-chat|replan-day)$"),
        limit=int(os.getenv("RATELIMIT_OPTIMIZER_LIMIT", "10")),
        window_seconds=int(os.getenv("RATELIMIT_OPTIMIZER_WINDOW", "60")),
        name="trip_optimization",
    ),
    # 3. Authentication & Credential Endpoints: 10 req/min
    RateLimitRule(
        pattern=re.compile(r"^/auth/(?:login|register|claim-session|token)$"),
        limit=int(os.getenv("RATELIMIT_AUTH_LIMIT", "10")),
        window_seconds=int(os.getenv("RATELIMIT_AUTH_WINDOW", "60")),
        name="auth_endpoints",
    ),
    # 4. External Weather API Endpoints: 20 req/min
    RateLimitRule(
        pattern=re.compile(r"^/weather(?:/.*)?$"),
        limit=int(os.getenv("RATELIMIT_WEATHER_LIMIT", "20")),
        window_seconds=int(os.getenv("RATELIMIT_WEATHER_WINDOW", "60")),
        name="weather_endpoints",
    ),
    # 5. Geocoding & Place Search: 30 req/min
    RateLimitRule(
        pattern=re.compile(r"^/place(?:/.*)?$"),
        limit=int(os.getenv("RATELIMIT_PLACE_LIMIT", "30")),
        window_seconds=int(os.getenv("RATELIMIT_PLACE_WINDOW", "60")),
        name="place_endpoints",
    ),
]


def extract_client_identifier(request: Request) -> str:
    """
    Extracts client identifier, prioritizing verified user IDs if available,
    falling back to X-Forwarded-For or remote socket host.
    """
    # 1. Prefer authenticated User ID from request headers
    user_id = request.headers.get("X-User-ID")
    if user_id and str(user_id).strip():
        return f"usr:{str(user_id).strip()}"

    # 2. Forwarded client IP (e.g., behind reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return f"ip:{client_ip}"

    # 3. Socket client host
    if request.client and request.client.host:
        return f"ip:{request.client.host}"

    return "ip:anonymous"


def get_matching_rule(path: str) -> Optional[RateLimitRule]:
    """Finds the first matching rate limit rule for an incoming request path."""
    for rule in DEFAULT_RULES:
        if rule.pattern.match(path):
            return rule
    return None


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette middleware enforcing sliding-window rate limits
    on designated expensive and security-critical endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        # Allow disabling rate limiting during specific test suites or via environment
        if os.getenv("TESTING_DISABLE_RATELIMIT", "false").lower() in ("true", "1", "yes"):
            return await call_next(request)

        # Skip rate limiting for HTTP OPTIONS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        rule = get_matching_rule(path)

        if not rule:
            # Unrestricted general route
            return await call_next(request)

        client_key = extract_client_identifier(request)
        allowed, remaining, retry_after = global_limiter.is_allowed(
            key=client_key,
            rule_name=rule.name,
            limit=rule.limit,
            window_seconds=rule.window_seconds,
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_key} on {path} (rule: {rule.name}, limit: {rule.limit}/{rule.window_seconds}s)"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "detail": f"Rate limit exceeded: maximum {rule.limit} requests per {rule.window_seconds} seconds for this endpoint. Please retry in {retry_after} seconds.",
                    "retry_after": retry_after,
                    "rule": rule.name,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rule.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
