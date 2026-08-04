"""Tests for security policies and validators — S18-04."""
import pytest

from app.security.policies import (
    HTTP_FORBIDDEN,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
    HTTP_UNPROCESSABLE,
    RATE_LIMIT_RPM,
    SECURITY_CHECKS,
    SecurityPolicy,
    critical_policies,
    get_policy,
    list_policies,
    policy_expected_code,
)
from app.security.validators import (
    audit_result,
    check_cross_tenant_isolation,
    is_sql_injection,
    is_tampered_jwt,
    is_xss_payload,
    validate_jwt_structure,
    validate_rate_limit,
)


class TestSecurityConstants:
    def test_http_unauthorized_is_401(self):
        assert HTTP_UNAUTHORIZED == 401

    def test_http_forbidden_is_403(self):
        assert HTTP_FORBIDDEN == 403

    def test_http_too_many_requests_is_429(self):
        assert HTTP_TOO_MANY_REQUESTS == 429

    def test_http_unprocessable_is_422(self):
        assert HTTP_UNPROCESSABLE == 422

    def test_rate_limit_rpm(self):
        assert RATE_LIMIT_RPM == 100

    def test_six_security_checks(self):
        assert len(SECURITY_CHECKS) == 6

    def test_rls_cross_tenant_check(self):
        assert "RLS_CROSS_TENANT" in SECURITY_CHECKS

    def test_jwt_tamper_check(self):
        assert "JWT_TAMPER" in SECURITY_CHECKS

    def test_rate_limit_bypass_check(self):
        assert "RATE_LIMIT_BYPASS" in SECURITY_CHECKS

    def test_sql_injection_check(self):
        assert "SQL_INJECTION" in SECURITY_CHECKS

    def test_xss_reflection_check(self):
        assert "XSS_REFLECTION" in SECURITY_CHECKS

    def test_tenant_escalation_check(self):
        assert "TENANT_ESCALATION" in SECURITY_CHECKS

    def test_security_checks_frozenset(self):
        assert isinstance(SECURITY_CHECKS, frozenset)


class TestSecurityPolicy:
    def test_valid_construction(self):
        p = SecurityPolicy(
            check_name="RLS_CROSS_TENANT",
            expected_http_code=403,
            description="Test",
            severity="CRITICAL",
        )
        assert p.check_name == "RLS_CROSS_TENANT"

    def test_invalid_check_name_raises(self):
        with pytest.raises(ValueError, match="Unknown security check"):
            SecurityPolicy("INVALID", 403, "desc", "HIGH")

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="severity"):
            SecurityPolicy("RLS_CROSS_TENANT", 403, "desc", "SUPER")

    def test_invalid_http_code_raises(self):
        with pytest.raises(ValueError, match="HTTP code"):
            SecurityPolicy("RLS_CROSS_TENANT", 999, "desc", "CRITICAL")

    def test_is_frozen(self):
        p = SecurityPolicy("RLS_CROSS_TENANT", 403, "desc", "CRITICAL")
        with pytest.raises(Exception):
            p.severity = "LOW"


class TestGetPolicy:
    def test_rls_returns_403(self):
        p = get_policy("RLS_CROSS_TENANT")
        assert p.expected_http_code == HTTP_FORBIDDEN

    def test_jwt_tamper_returns_401(self):
        p = get_policy("JWT_TAMPER")
        assert p.expected_http_code == HTTP_UNAUTHORIZED

    def test_rate_limit_returns_429(self):
        p = get_policy("RATE_LIMIT_BYPASS")
        assert p.expected_http_code == HTTP_TOO_MANY_REQUESTS

    def test_sql_injection_returns_422(self):
        p = get_policy("SQL_INJECTION")
        assert p.expected_http_code == HTTP_UNPROCESSABLE

    def test_xss_returns_422(self):
        p = get_policy("XSS_REFLECTION")
        assert p.expected_http_code == HTTP_UNPROCESSABLE

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown check"):
            get_policy("NONEXISTENT")

    def test_all_checks_have_policy(self):
        for check in SECURITY_CHECKS:
            p = get_policy(check)
            assert p.check_name == check


class TestListPolicies:
    def test_returns_list(self):
        assert isinstance(list_policies(), list)

    def test_six_policies(self):
        assert len(list_policies()) == 6

    def test_all_security_check_names_covered(self):
        names = {p.check_name for p in list_policies()}
        assert names == SECURITY_CHECKS


class TestCriticalPolicies:
    def test_returns_list(self):
        assert isinstance(critical_policies(), list)

    def test_all_are_critical(self):
        for p in critical_policies():
            assert p.severity == "CRITICAL"

    def test_at_least_one_critical(self):
        assert len(critical_policies()) >= 1

    def test_rls_is_critical(self):
        names = {p.check_name for p in critical_policies()}
        assert "RLS_CROSS_TENANT" in names


class TestPolicyExpectedCode:
    def test_rls_is_403(self):
        assert policy_expected_code("RLS_CROSS_TENANT") == 403

    def test_jwt_is_401(self):
        assert policy_expected_code("JWT_TAMPER") == 401


class TestIsSQLInjection:
    def test_union_select_detected(self):
        assert is_sql_injection("' UNION SELECT * FROM users --") is True

    def test_drop_table_detected(self):
        assert is_sql_injection("'; DROP TABLE users;") is True

    def test_safe_input_not_detected(self):
        assert is_sql_injection("My project name") is False

    def test_empty_string_safe(self):
        assert is_sql_injection("") is False

    def test_or_equals_detected(self):
        assert is_sql_injection("1' OR 1=1") is True


class TestIsXSSPayload:
    def test_script_tag_detected(self):
        assert is_xss_payload("<script>alert('xss')</script>") is True

    def test_javascript_protocol_detected(self):
        assert is_xss_payload("javascript:alert(1)") is True

    def test_safe_text_not_detected(self):
        assert is_xss_payload("Hello, World!") is False

    def test_iframe_detected(self):
        assert is_xss_payload("<iframe src='evil.com'>") is True


class TestValidateJWTStructure:
    def test_valid_three_part_token(self):
        assert validate_jwt_structure("header.payload.signature") is True

    def test_two_parts_invalid(self):
        assert validate_jwt_structure("header.payload") is False

    def test_too_short_invalid(self):
        assert validate_jwt_structure("x") is False

    def test_empty_invalid(self):
        assert validate_jwt_structure("") is False


class TestIsTamperedJWT:
    def test_correct_sig_not_tampered(self):
        token = "header.payload.validsig"
        assert is_tampered_jwt(token, "validsig") is False

    def test_wrong_sig_is_tampered(self):
        token = "header.payload.badsig"
        assert is_tampered_jwt(token, "validsig") is True

    def test_malformed_token_is_tampered(self):
        assert is_tampered_jwt("bad", "sig") is True


class TestValidateRateLimit:
    def test_within_limit_passes(self):
        assert validate_rate_limit(100) is True

    def test_over_limit_fails(self):
        assert validate_rate_limit(101) is False

    def test_zero_passes(self):
        assert validate_rate_limit(0) is True

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_minutes"):
            validate_rate_limit(50, window_minutes=0)

    def test_negative_count_raises(self):
        with pytest.raises(ValueError, match="request_count"):
            validate_rate_limit(-1)


class TestCrossTenantIsolation:
    def test_same_tenant_allowed(self):
        assert check_cross_tenant_isolation("tenant-A", "tenant-A") is True

    def test_different_tenant_blocked(self):
        assert check_cross_tenant_isolation("tenant-A", "tenant-B") is False


class TestAuditResult:
    def test_passed_when_codes_match(self):
        result = audit_result("JWT_TAMPER", 401)
        assert result["passed"] is True

    def test_failed_when_codes_differ(self):
        result = audit_result("JWT_TAMPER", 200)
        assert result["passed"] is False

    def test_check_in_result(self):
        result = audit_result("RLS_CROSS_TENANT", 403)
        assert result["check"] == "RLS_CROSS_TENANT"

    def test_expected_in_result(self):
        result = audit_result("RLS_CROSS_TENANT", 403)
        assert result["expected"] == 403

    def test_severity_in_result(self):
        result = audit_result("RLS_CROSS_TENANT", 403)
        assert result["severity"] == "CRITICAL"
