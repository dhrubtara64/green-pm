from __future__ import annotations

import time
from typing import Optional

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Sliding-window in-process rate limiter (per IP or per user).

    For production use, replace the in-memory store with Redis so limits
    are shared across replicas. This implementation is intentionally
    simple: correct behavior in a single-process dev/test environment.
    """

    def __init__(self, requests_per_minute: int = 60) -> None:
        self._limit = requests_per_minute
        self._window = 60.0
        # key -> list of timestamps within the current window
        self._store: dict[str, list[float]] = {}

    def _key(self, request: Request) -> str:
        user_id: Optional[str] = None
        if hasattr(request.state, "user"):
            user_id = str(getattr(request.state.user, "user_id", None))
        if user_id:
            return f"user:{user_id}"
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    def is_allowed(self, request: Request) -> tuple[bool, int, int]:
        """Return (allowed, remaining, retry_after_seconds)."""
        now = time.monotonic()
        key = self._key(request)
        window_start = now - self._window
        timestamps = [t for t in self._store.get(key, []) if t > window_start]
        if len(timestamps) >= self._limit:
            oldest = timestamps[0]
            retry_after = max(1, int(self._window - (now - oldest)) + 1)
            self._store[key] = timestamps
            return False, 0, retry_after
        timestamps.append(now)
        self._store[key] = timestamps
        remaining = self._limit - len(timestamps)
        return True, remaining, 0

    async def __call__(self, request: Request, call_next):
        allowed, remaining, retry_after = self.is_allowed(request)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self._limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
