"""Security validation functions — S18-04."""
from __future__ import annotations

import re
from typing import Optional

from app.security.policies import (
    JWT_ALGORITHM,
    MIN_TOKEN_LENGTH,
    RATE_LIMIT_RPM,
    SecurityPolicy,
    get_policy,
)

_SQL_INJECTION_PATTERNS: tuple[str, ...] = (
    r"(?i)(union\s+select)",
    r"(?i)(drop\s+table)",
    r"(?i)(insert\s+into)",
    r"(?i)(delete\s+from)",
    r"(?i)(exec\s*\()",
    r"(?i)(;\s*--)",
    r"(?i)(\bor\b\s+\d+\s*=\s*\d+)",
    r"(?i)('\s+or\s+')",
)

_XSS_PATTERNS: tuple[str, ...] = (
    r"(?i)<script[^>]*>",
    r"(?i)javascript:",
    r"(?i)on\w+\s*=",
    r"(?i)<iframe",
    r"(?i)eval\s*\(",
)

_COMPILED_SQL = [re.compile(p) for p in _SQL_INJECTION_PATTERNS]
_COMPILED_XSS = [re.compile(p) for p in _XSS_PATTERNS]


def is_sql_injection(payload: str) -> bool:
    return any(p.search(payload) for p in _COMPILED_SQL)


def is_xss_payload(payload: str) -> bool:
    return any(p.search(payload) for p in _COMPILED_XSS)


def validate_jwt_structure(token: str) -> bool:
    """Returns True if token has valid 3-part JWT structure."""
    if not token or len(token) < MIN_TOKEN_LENGTH:
        return False
    parts = token.split(".")
    return len(parts) == 3 and all(len(p) > 0 for p in parts)


def is_tampered_jwt(token: str, valid_signature: str) -> bool:
    """Return True if the token's signature does not match valid_signature."""
    if not validate_jwt_structure(token):
        return True
    parts = token.split(".")
    return parts[2] != valid_signature


def validate_rate_limit(request_count: int, window_minutes: int = 1) -> bool:
    """Return True if request_count is within the rate limit for the window."""
    if window_minutes < 1:
        raise ValueError("window_minutes must be >= 1")
    if request_count < 0:
        raise ValueError("request_count must be >= 0")
    allowed = RATE_LIMIT_RPM * window_minutes
    return request_count <= allowed


def check_cross_tenant_isolation(
    requesting_tenant_id: str, resource_tenant_id: str
) -> bool:
    """Return True if the resource belongs to the requesting tenant."""
    return requesting_tenant_id == resource_tenant_id


def audit_result(check_name: str, actual_http_code: int) -> dict:
    """Compare actual response code to policy expectation."""
    policy = get_policy(check_name)
    passed = actual_http_code == policy.expected_http_code
    return {
        "check": check_name,
        "expected": policy.expected_http_code,
        "actual": actual_http_code,
        "passed": passed,
        "severity": policy.severity,
    }
