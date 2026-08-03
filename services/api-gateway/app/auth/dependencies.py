from __future__ import annotations

import uuid
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt import AuthSettings, TokenClaims, TokenInvalidError, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)

_ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 0,
    "vendor_portal": 1,
    "engineer": 2,
    "executive": 3,
    "project_manager": 4,
    "tenant_admin": 5,
    "super_admin": 6,
}


class CurrentUser:
    def __init__(self, claims: TokenClaims) -> None:
        self.user_id: uuid.UUID = uuid.UUID(claims.sub)
        self.tenant_id: uuid.UUID = uuid.UUID(claims.tenant_id)
        self.role: str = claims.role

    def has_role(self, minimum_role: str) -> bool:
        return _ROLE_HIERARCHY.get(self.role, -1) >= _ROLE_HIERARCHY.get(minimum_role, 999)


def _get_settings(request: Request) -> AuthSettings:
    settings: Optional[AuthSettings] = getattr(request.app.state, "auth_settings", None)
    if settings is None:
        raise RuntimeError("app.state.auth_settings not configured")
    return settings


async def get_current_user(request: Request) -> CurrentUser:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.removeprefix("Bearer ").strip()
    settings = _get_settings(request)
    try:
        claims = decode_token(token, settings)
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return CurrentUser(claims)


def require_role(minimum_role: str) -> Callable:
    async def _dep(request: Request) -> CurrentUser:
        user = await get_current_user(request)
        if not user.has_role(minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role!r} is below required {minimum_role!r}",
            )
        return user
    return _dep
