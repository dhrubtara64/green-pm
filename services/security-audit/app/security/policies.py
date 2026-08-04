"""Security policy definitions — S18-04."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SECURITY_CHECKS: frozenset[str] = frozenset({
    "RLS_CROSS_TENANT",
    "JWT_TAMPER",
    "RATE_LIMIT_BYPASS",
    "SQL_INJECTION",
    "XSS_REFLECTION",
    "TENANT_ESCALATION",
})

HTTP_UNAUTHORIZED: int = 401
HTTP_FORBIDDEN: int = 403
HTTP_TOO_MANY_REQUESTS: int = 429
HTTP_UNPROCESSABLE: int = 422

RATE_LIMIT_RPM: int = 100
JWT_ALGORITHM: str = "RS256"
MIN_TOKEN_LENGTH: int = 20


@dataclass(frozen=True)
class SecurityPolicy:
    check_name: str
    expected_http_code: int
    description: str
    severity: str

    def __post_init__(self) -> None:
        if self.check_name not in SECURITY_CHECKS:
            raise ValueError(f"Unknown security check '{self.check_name}'")
        valid_severity = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if self.severity not in valid_severity:
            raise ValueError(f"severity must be one of {valid_severity}")
        if self.expected_http_code < 100 or self.expected_http_code > 599:
            raise ValueError(f"Invalid HTTP code: {self.expected_http_code}")


_DEFAULT_POLICIES: dict[str, SecurityPolicy] = {
    "RLS_CROSS_TENANT": SecurityPolicy(
        check_name="RLS_CROSS_TENANT",
        expected_http_code=HTTP_FORBIDDEN,
        description="Cross-tenant data access must be denied by RLS",
        severity="CRITICAL",
    ),
    "JWT_TAMPER": SecurityPolicy(
        check_name="JWT_TAMPER",
        expected_http_code=HTTP_UNAUTHORIZED,
        description="Tampered JWT tokens must return 401",
        severity="CRITICAL",
    ),
    "RATE_LIMIT_BYPASS": SecurityPolicy(
        check_name="RATE_LIMIT_BYPASS",
        expected_http_code=HTTP_TOO_MANY_REQUESTS,
        description="Rate limit bypass attempts must return 429",
        severity="HIGH",
    ),
    "SQL_INJECTION": SecurityPolicy(
        check_name="SQL_INJECTION",
        expected_http_code=HTTP_UNPROCESSABLE,
        description="SQL injection payloads must be rejected",
        severity="CRITICAL",
    ),
    "XSS_REFLECTION": SecurityPolicy(
        check_name="XSS_REFLECTION",
        expected_http_code=HTTP_UNPROCESSABLE,
        description="XSS payloads must not be reflected in responses",
        severity="HIGH",
    ),
    "TENANT_ESCALATION": SecurityPolicy(
        check_name="TENANT_ESCALATION",
        expected_http_code=HTTP_FORBIDDEN,
        description="Privilege escalation across tenants must be denied",
        severity="CRITICAL",
    ),
}


def get_policy(check_name: str) -> SecurityPolicy:
    if check_name not in SECURITY_CHECKS:
        raise ValueError(f"Unknown check: '{check_name}'")
    return _DEFAULT_POLICIES[check_name]


def list_policies() -> list[SecurityPolicy]:
    return [_DEFAULT_POLICIES[k] for k in sorted(SECURITY_CHECKS)]


def critical_policies() -> list[SecurityPolicy]:
    return [p for p in _DEFAULT_POLICIES.values() if p.severity == "CRITICAL"]


def policy_expected_code(check_name: str) -> int:
    return get_policy(check_name).expected_http_code
