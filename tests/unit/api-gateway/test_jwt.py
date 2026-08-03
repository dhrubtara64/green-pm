"""JWT auth unit tests — S1-AUTH-01.

Covers: token creation, decode, expiry, wrong key, bad role, claims integrity.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from jose import jwt as jose_jwt

pytestmark = pytest.mark.unit

from app.auth.jwt import (
    AuthSettings,
    TokenClaims,
    TokenInvalidError,
    create_access_token,
    decode_token,
)

SETTINGS = AuthSettings(secret_key="test-secret-do-not-use-in-prod")
TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")


# ── Invariant 1: valid token round-trips ─────────────────────────────────────

def test_valid_token_round_trip():
    token = create_access_token(USER_ID, TENANT_ID, "engineer", SETTINGS)
    claims = decode_token(token, SETTINGS)
    assert claims.sub == str(USER_ID)
    assert claims.tenant_id == str(TENANT_ID)
    assert claims.role == "engineer"


def test_all_valid_roles_accepted():
    for role in ["super_admin", "tenant_admin", "project_manager",
                 "engineer", "vendor_portal", "executive", "viewer"]:
        token = create_access_token(USER_ID, TENANT_ID, role, SETTINGS)
        claims = decode_token(token, SETTINGS)
        assert claims.role == role


# ── Invariant 2: invalid role rejected at creation time ──────────────────────

def test_unknown_role_rejected_at_creation():
    with pytest.raises(ValueError, match="Unknown role"):
        create_access_token(USER_ID, TENANT_ID, "god_mode", SETTINGS)


# ── Invariant 3: expired token rejected ──────────────────────────────────────

def test_expired_token_rejected():
    token = create_access_token(
        USER_ID, TENANT_ID, "engineer", SETTINGS,
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(TokenInvalidError):
        decode_token(token, SETTINGS)


# ── Invariant 4: wrong secret rejected ───────────────────────────────────────

def test_wrong_secret_rejected():
    token = create_access_token(USER_ID, TENANT_ID, "engineer", SETTINGS)
    evil_settings = AuthSettings(secret_key="evil-secret")
    with pytest.raises(TokenInvalidError):
        decode_token(token, evil_settings)


# ── Invariant 5: tampered payload rejected ───────────────────────────────────

def test_tampered_payload_rejected():
    token = create_access_token(USER_ID, TENANT_ID, "engineer", SETTINGS)
    # Decode without verification, change role, re-encode with same key
    raw = jose_jwt.decode(token, SETTINGS.secret_key, algorithms=[SETTINGS.algorithm])
    raw["role"] = "super_admin"
    forged = jose_jwt.encode(raw, "different-key", algorithm=SETTINGS.algorithm)
    with pytest.raises(TokenInvalidError):
        decode_token(forged, SETTINGS)


# ── Invariant 6: unknown role in payload rejected at decode time ──────────────

def test_unknown_role_in_payload_rejected_at_decode():
    import time as _time
    raw = {
        "sub": str(USER_ID),
        "tenant_id": str(TENANT_ID),
        "role": "hacker",
        "iat": _time.time(),
        "exp": _time.time() + 3600,
        "jti": str(uuid.uuid4()),
    }
    token = jose_jwt.encode(raw, SETTINGS.secret_key, algorithm=SETTINGS.algorithm)
    with pytest.raises(TokenInvalidError, match="Unknown role"):
        decode_token(token, SETTINGS)


# ── Invariant 7: jti is generated and unique ─────────────────────────────────

def test_jti_is_unique():
    t1 = create_access_token(USER_ID, TENANT_ID, "engineer", SETTINGS)
    t2 = create_access_token(USER_ID, TENANT_ID, "engineer", SETTINGS)
    c1 = decode_token(t1, SETTINGS)
    c2 = decode_token(t2, SETTINGS)
    assert c1.jti != c2.jti


# ── Invariant 8: claims are UTC-aware datetimes ───────────────────────────────

def test_claims_exp_and_iat_are_utc():
    from datetime import timezone
    token = create_access_token(USER_ID, TENANT_ID, "engineer", SETTINGS)
    claims = decode_token(token, SETTINGS)
    assert claims.exp.tzinfo == timezone.utc
    assert claims.iat.tzinfo == timezone.utc
    assert claims.exp > claims.iat
