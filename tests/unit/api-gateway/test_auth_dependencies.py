"""Auth dependency unit tests — S1-AUTH-01.

Tests get_current_user() and require_role() FastAPI dependencies using
a mock Request (no running server needed).
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3] / "services" / "api-gateway"))

from app.auth.jwt import AuthSettings, create_access_token
from app.auth.dependencies import CurrentUser, get_current_user, require_role

SETTINGS = AuthSettings(secret_key="test-secret-dep")
TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000001")


def _make_request(auth_header: str | None = None) -> MagicMock:
    request = MagicMock()
    request.app.state.auth_settings = SETTINGS
    if auth_header is None:
        request.headers = {}
    else:
        request.headers = {"Authorization": auth_header}
    return request


def _token(role: str = "engineer") -> str:
    return create_access_token(USER_ID, TENANT_ID, role, SETTINGS)


# ── get_current_user ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_bearer_returns_user():
    req = _make_request(f"Bearer {_token()}")
    user = await get_current_user(req)
    assert isinstance(user, CurrentUser)
    assert user.user_id == USER_ID
    assert user.tenant_id == TENANT_ID
    assert user.role == "engineer"


@pytest.mark.asyncio
async def test_missing_header_raises_401():
    from fastapi import HTTPException
    req = _make_request(None)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_malformed_header_raises_401():
    from fastapi import HTTPException
    req = _make_request("Token abc123")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_raises_401():
    from fastapi import HTTPException
    req = _make_request("Bearer not.a.real.token")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(req)
    assert exc_info.value.status_code == 401


# ── require_role ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_role_passes_when_sufficient():
    req = _make_request(f"Bearer {_token('project_manager')}")
    dep = require_role("engineer")
    user = await dep(req)
    assert user.role == "project_manager"


@pytest.mark.asyncio
async def test_require_role_raises_403_when_insufficient():
    from fastapi import HTTPException
    req = _make_request(f"Bearer {_token('viewer')}")
    dep = require_role("project_manager")
    with pytest.raises(HTTPException) as exc_info:
        await dep(req)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_exact_match_passes():
    req = _make_request(f"Bearer {_token('tenant_admin')}")
    dep = require_role("tenant_admin")
    user = await dep(req)
    assert user.role == "tenant_admin"


# ── CurrentUser.has_role ──────────────────────────────────────────────────────

def _make_user(role: str) -> CurrentUser:
    from app.auth.jwt import TokenClaims
    from datetime import datetime, timezone
    claims = TokenClaims(
        sub=str(USER_ID),
        tenant_id=str(TENANT_ID),
        role=role,
        exp=datetime.now(timezone.utc),
        iat=datetime.now(timezone.utc),
    )
    return CurrentUser(claims)


def test_has_role_hierarchy():
    sa = _make_user("super_admin")
    assert sa.has_role("tenant_admin") is True
    assert sa.has_role("super_admin") is True

    viewer = _make_user("viewer")
    assert viewer.has_role("engineer") is False
    assert viewer.has_role("viewer") is True
