"""
Rate Limiter Service & Middleware

ARCHITECTURAL & MULTI-WORKER DEPLOYMENT SPECIFICATION:
- In-Memory Sliding Window:
  `SlidingWindowRateLimiter` maintains hit timestamps in-process using collections.deque and threading.Lock.
  This provides zero-overhead, sub-millisecond limiting suitable for single-process deployments without
  requiring an external Redis dependency.
- Multi-Worker & Multi-Instance Deployments:
  When running multiple Uvicorn worker processes (e.g. `uvicorn backend.app:app --workers 4`) or horizontally
  scaled container replicas behind a load balancer, each worker process maintains an independent memory bucket.
  In this scenario:
    1. Effective limit is multiplied by the number of active workers unless sticky sessions are configured.
    2. Strict global cluster-wide enforcement requires an external shared store (e.g., Redis sliding-window
       token bucket) or offloading rate limiting to an edge reverse proxy / API gateway (NGINX `limit_req`,
       Cloudflare WAF, or Envoy).
- Geocoding & External Services (Nominatim):
  OpenStreetMap Nominatim strictly prohibits more than 1 request per second to public endpoints.
  The in-process rate limiter in `backend/services/external/location_service.py` protects against exceeding
  this threshold within a single process. Multi-worker clusters querying public Nominatim without coordinated
  queuing will violate this policy; production deployments MUST either route through a shared proxy or set
  `NOMINATIM_BASE_URL` to an internal self-hosted Nominatim instance.
"""

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


def is_trusted_proxy(client_host: Optional[str]) -> bool:
    """
    Determines whether a client socket host represents a trusted reverse proxy.
    Only requests arriving from trusted proxies may supply client IP via X-Forwarded-For.
    When TRUST_PROXY_HEADERS=true or the socket host is in TRUSTED_PROXIES, X-Forwarded-For is honored.
    Direct clients attempting to spoof X-Forwarded-For are constrained to their socket host.
    """
    if os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("true", "1", "yes"):
        return True

    trusted_list = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1,localhost,testclient")
    trusted_set = {p.strip().lower() for p in trusted_list.split(",") if p.strip()}

    if client_host and str(client_host).strip().lower() in trusted_set:
        return True

    return False


def extract_client_identifier(request: Request) -> str:
    """
    Extracts client identifier, prioritizing cryptographically verified user IDs
    from valid Bearer JWT tokens, falling back strictly to client IP.

    Security Rules:
    1. Never trusts client-supplied 'X-User-ID' headers as proof of identity to partition limits.
       Accepting unauthenticated 'X-User-ID' headers would allow attackers to forge headers
       and evade IP rate limiting. Only cryptographically verified Bearer tokens (or matching
       X-User-ID) are used for user keys.
    2. 'X-Forwarded-For' is honored ONLY when the request arrives from a trusted proxy
       (via TRUST_PROXY_HEADERS=true or TRUSTED_PROXIES). Direct untrusted clients cannot
       spoof X-Forwarded-For to evade rate limits.
    """
    # 1. Prefer authenticated User ID from verified Bearer token
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and str(auth_header).strip().lower().startswith("bearer "):
        raw_token = str(auth_header).strip()[7:].strip()
        if raw_token:
            try:
                from backend.services.auth.jwt_service import verify_access_token
                claims = verify_access_token(raw_token)
                sub = claims.get("sub")
                if sub and str(sub).strip():
                    clean_sub = str(sub).strip()
                    declared_hdr = request.headers.get("x-user-id") or request.headers.get("X-User-ID")
                    if declared_hdr and str(declared_hdr).strip() != clean_sub:
                        # Mismatch between token and header (potential confused-deputy attack)
                        pass
                    else:
                        return f"usr:{clean_sub}"
            except Exception:
                # Expired or invalid token: treat client as unauthenticated (fall back to IP)
                pass

    # 2. Derive client IP, respecting X-Forwarded-For only from trusted proxies
    socket_host = request.client.host.strip() if request.client and request.client.host else None

    if is_trusted_proxy(socket_host):
        forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
            if client_ip:
                return f"ip:{client_ip}"

    # 3. Direct client connection or untrusted proxy: use remote socket host
    if socket_host:
        return f"ip:{socket_host}"

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
