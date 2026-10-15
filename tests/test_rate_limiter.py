import pytest
from starlette.testclient import TestClient

from backend.app import app
from backend.services.security.rate_limiter import (
    global_limiter,
    extract_client_identifier,
    RateLimitRule,
    DEFAULT_RULES,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset the global rate limiter before each test."""
    global_limiter.reset()
    yield
    global_limiter.reset()


def test_rate_limit_headers_present_on_allowed_request():
    """Allowed requests include X-RateLimit-Limit and X-RateLimit-Remaining headers."""
    resp = client.post("/auth/login", json={"email": "nonexistent@test.com", "password": "any"})
    # Even on 401, the rate limiter middleware attached limit headers
    assert resp.status_code == 401
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert int(resp.headers["X-RateLimit-Remaining"]) >= 0


def test_auth_endpoint_rate_limiting_triggers_429():
    """Sending 11 consecutive auth requests (limit=10) triggers HTTP 429 on the 11th request."""
    # First 10 requests are processed
    for i in range(10):
        resp = client.post(
            "/auth/login",
            json={"email": f"test_{i}@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": "198.51.100.1"},
        )
        assert resp.status_code == 401, f"Request {i+1} failed unexpectedly: {resp.status_code}"

    # 11th request exceeds limit and receives 429
    blocked_resp = client.post(
        "/auth/login",
        json={"email": "test_11@example.com", "password": "wrong"},
        headers={"X-Forwarded-For": "198.51.100.1"},
    )
    assert blocked_resp.status_code == 429
    data = blocked_resp.json()
    assert data["error"] == "RATE_LIMIT_EXCEEDED"
    assert "Rate limit exceeded" in data["detail"]
    assert "retry_after" in data
    assert int(blocked_resp.headers.get("Retry-After", "0")) > 0
    assert blocked_resp.headers.get("X-RateLimit-Remaining") == "0"


def test_different_clients_have_isolated_buckets():
    """Requests from different client IPs do not exhaust each other's quotas."""
    # Client A exhausts their quota (10 requests)
    for _ in range(10):
        client.post(
            "/auth/login",
            json={"email": "a@example.com", "password": "p"},
            headers={"X-Forwarded-For": "203.0.113.10"},
        )

    # Client A is blocked
    resp_a = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "p"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert resp_a.status_code == 429

    # Client B from a different IP is NOT blocked
    resp_b = client.post(
        "/auth/login",
        json={"email": "b@example.com", "password": "p"},
        headers={"X-Forwarded-For": "203.0.113.20"},
    )
    assert resp_b.status_code == 401  # Normal credential check, not 429!


def test_authenticated_user_id_partitions_limits():
    """Authenticated users are throttled by X-User-ID rather than shared IP."""
    # User 1 exhausts their 10 requests from a shared NAT IP
    for _ in range(10):
        client.post(
            "/auth/login",
            json={"email": "u1@example.com", "password": "p"},
            headers={"X-User-ID": "user_nat_alpha", "X-Forwarded-For": "192.0.2.1"},
        )

    # User 1 is throttled
    resp1 = client.post(
        "/auth/login",
        json={"email": "u1@example.com", "password": "p"},
        headers={"X-User-ID": "user_nat_alpha", "X-Forwarded-For": "192.0.2.1"},
    )
    assert resp1.status_code == 429

    # User 2 on the same IP still has their full quota
    resp2 = client.post(
        "/auth/login",
        json={"email": "u2@example.com", "password": "p"},
        headers={"X-User-ID": "user_nat_beta", "X-Forwarded-For": "192.0.2.1"},
    )
    assert resp2.status_code == 401  # Not rate limited


def test_cors_options_preflight_bypasses_rate_limit():
    """OPTIONS preflight requests are never blocked by rate limiting."""
    for _ in range(15):
        resp = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200
        assert resp.status_code != 429
