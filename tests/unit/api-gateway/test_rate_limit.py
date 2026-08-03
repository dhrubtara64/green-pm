"""Rate limiter unit tests — S1-API-01."""
from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock

import pytest

pytestmark = pytest.mark.unit

from app.middleware.rate_limit import RateLimiter


def _make_request(ip: str = "1.2.3.4") -> MagicMock:
    req = MagicMock()
    req.client.host = ip
    req.headers = {}
    req.state = MagicMock(spec=[])  # no 'user' attribute
    return req


# ── Basic allow / deny ────────────────────────────────────────────────────────

def test_first_request_allowed():
    limiter = RateLimiter(requests_per_minute=5)
    allowed, remaining, _ = limiter.is_allowed(_make_request())
    assert allowed is True
    assert remaining == 4


def test_remaining_decrements():
    limiter = RateLimiter(requests_per_minute=5)
    req = _make_request()
    for _ in range(4):
        limiter.is_allowed(req)
    allowed, remaining, _ = limiter.is_allowed(req)
    assert allowed is True
    assert remaining == 0


def test_exceeding_limit_denied():
    limiter = RateLimiter(requests_per_minute=3)
    req = _make_request()
    for _ in range(3):
        limiter.is_allowed(req)
    allowed, remaining, retry_after = limiter.is_allowed(req)
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1


# ── Per-IP isolation ──────────────────────────────────────────────────────────

def test_different_ips_tracked_independently():
    limiter = RateLimiter(requests_per_minute=2)
    a = _make_request("10.0.0.1")
    b = _make_request("10.0.0.2")
    limiter.is_allowed(a)
    limiter.is_allowed(a)
    # a is now at limit
    allowed_a, _, _ = limiter.is_allowed(a)
    assert allowed_a is False
    # b should still have full budget
    allowed_b, remaining_b, _ = limiter.is_allowed(b)
    assert allowed_b is True
    assert remaining_b == 1


# ── Per-user when auth present ────────────────────────────────────────────────

def test_user_key_preferred_over_ip():
    limiter = RateLimiter(requests_per_minute=2)

    req = _make_request("1.2.3.4")
    req.state = MagicMock()
    req.state.user = MagicMock()
    req.state.user.user_id = "user-abc"

    limiter.is_allowed(req)
    limiter.is_allowed(req)
    allowed, _, _ = limiter.is_allowed(req)
    assert allowed is False

    # Same IP but no user should NOT be affected by user limit
    req2 = _make_request("1.2.3.4")
    allowed2, _, _ = limiter.is_allowed(req2)
    assert allowed2 is True


# ── X-Forwarded-For support ───────────────────────────────────────────────────

def test_x_forwarded_for_used_for_key():
    limiter = RateLimiter(requests_per_minute=2)
    req = _make_request("10.0.0.99")
    req.headers = {"X-Forwarded-For": "203.0.113.5, 10.0.0.1"}

    limiter.is_allowed(req)
    limiter.is_allowed(req)
    allowed, _, _ = limiter.is_allowed(req)
    assert allowed is False

    # Direct connection from same proxy IP (no X-Forwarded-For) should be separate
    req2 = _make_request("10.0.0.99")
    allowed2, _, _ = limiter.is_allowed(req2)
    assert allowed2 is True


# ── Middleware raises 429 on denial ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_middleware_raises_429_when_limit_exceeded():
    from fastapi import HTTPException
    limiter = RateLimiter(requests_per_minute=1)
    req = _make_request()
    call_next = AsyncMock()

    # First request passes
    response = await limiter(req, call_next)
    assert call_next.await_count == 1

    # Second request should raise 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter(req, call_next)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
