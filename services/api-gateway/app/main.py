from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.jwt import AuthSettings
from .middleware.rate_limit import RateLimiter

app = FastAPI(
    title="Green PM — API Gateway",
    version="0.5.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") != "production" else None,
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
_rate_limiter = RateLimiter(requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "120")))
app.middleware("http")(_rate_limiter)

# ── Auth settings on app state ────────────────────────────────────────────────
app.state.auth_settings = AuthSettings(
    secret_key=os.environ["JWT_SECRET_KEY"],
    algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok", "service": "api-gateway"}
