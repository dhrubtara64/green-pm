from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel


class TokenClaims(BaseModel):
    sub: str           # user_id (UUID as string)
    tenant_id: str     # UUID as string
    role: str
    exp: datetime
    iat: datetime
    jti: str = ""      # JWT ID for future revocation support


class AuthSettings(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


_VALID_ROLES = frozenset({
    "super_admin", "tenant_admin", "project_manager",
    "engineer", "vendor_portal", "executive", "viewer",
})


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    settings: AuthSettings,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if role not in _VALID_ROLES:
        raise ValueError(f"Unknown role: {role!r}")
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str, settings: AuthSettings) -> TokenClaims:
    try:
        raw = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise TokenInvalidError(str(exc)) from exc

    role = raw.get("role", "")
    if role not in _VALID_ROLES:
        raise TokenInvalidError(f"Unknown role in token: {role!r}")

    return TokenClaims(
        sub=raw["sub"],
        tenant_id=raw["tenant_id"],
        role=role,
        exp=datetime.fromtimestamp(raw["exp"], tz=timezone.utc),
        iat=datetime.fromtimestamp(raw["iat"], tz=timezone.utc),
        jti=raw.get("jti", ""),
    )


class TokenInvalidError(Exception):
    pass
