"""RBAC unit tests — S1-AUTH-02.

Locks in the permission matrix so no accidental privilege changes go undetected.
Tests both positive grants and negative denials across the role hierarchy.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3] / "services" / "api-gateway"))

from app.auth.rbac import (
    Action,
    PermissionDeniedError,
    Resource,
    assert_permission,
    check_permission,
)


# ── Grants are flat per role (no accumulation) ────────────────────────────────
# Roles are not a strict ladder — executive and engineer are separate tracks.
# Each role's grants are explicitly defined; project_manager duplicates engineer
# grants it needs rather than inheriting them.

def test_project_manager_has_evidence_create():
    assert check_permission("project_manager", Resource.EVIDENCE, Action.CREATE) is True


def test_tenant_admin_has_project_create():
    assert check_permission("tenant_admin", Resource.PROJECT, Action.CREATE) is True


def test_super_admin_has_audit_log_read():
    assert check_permission("super_admin", Resource.AUDIT_LOG, Action.READ) is True


def test_executive_does_not_inherit_engineer_write():
    # executive is a read-heavy role — does NOT get engineer write access
    assert check_permission("executive", Resource.ACTIVITY, Action.UPDATE) is False
    assert check_permission("executive", Resource.ACTIVITY, Action.CREATE) is False
    assert check_permission("executive", Resource.RISK, Action.CREATE) is False


# ── Explicit grant checks ─────────────────────────────────────────────────────

@pytest.mark.parametrize("role,resource,action,expected", [
    # viewer
    ("viewer", Resource.PROJECT, Action.READ, True),
    ("viewer", Resource.ACTIVITY, Action.CREATE, False),
    ("viewer", Resource.REPORT, Action.EXPORT, False),
    # vendor_portal
    ("vendor_portal", Resource.VENDOR, Action.UPDATE, True),
    ("vendor_portal", Resource.VENDOR, Action.DELETE, False),
    ("vendor_portal", Resource.USER, Action.READ, False),
    # engineer
    ("engineer", Resource.ACTIVITY, Action.CREATE, True),
    ("engineer", Resource.ACTIVITY, Action.DELETE, False),
    ("engineer", Resource.RISK, Action.CREATE, True),
    ("engineer", Resource.RISK, Action.APPROVE, False),
    ("engineer", Resource.TENANT, Action.READ, False),
    # executive
    ("executive", Resource.REPORT, Action.EXPORT, True),
    ("executive", Resource.ACTIVITY, Action.UPDATE, False),
    ("executive", Resource.AUDIT_LOG, Action.READ, True),
    # project_manager
    ("project_manager", Resource.ACTIVITY, Action.APPROVE, True),
    ("project_manager", Resource.EVIDENCE, Action.DELETE, True),
    ("project_manager", Resource.TENANT, Action.UPDATE, False),
    ("project_manager", Resource.USER, Action.CREATE, False),
    # tenant_admin
    ("tenant_admin", Resource.USER, Action.DELETE, True),
    ("tenant_admin", Resource.PROJECT, Action.DELETE, True),
    ("tenant_admin", Resource.TENANT, Action.DELETE, False),
    ("tenant_admin", Resource.TENANT, Action.ADMIN, False),
    # super_admin
    ("super_admin", Resource.TENANT, Action.ADMIN, True),
    ("super_admin", Resource.TENANT, Action.DELETE, True),
    ("super_admin", Resource.USER, Action.ADMIN, True),
])
def test_permission_matrix(role, resource, action, expected):
    assert check_permission(role, resource, action) is expected


# ── Unknown role ──────────────────────────────────────────────────────────────

def test_unknown_role_denied():
    assert check_permission("hacker", Resource.PROJECT, Action.READ) is False


# ── assert_permission raises on denial ───────────────────────────────────────

def test_assert_permission_passes_when_granted():
    assert_permission("engineer", Resource.ACTIVITY, Action.CREATE)


def test_assert_permission_raises_on_denial():
    with pytest.raises(PermissionDeniedError):
        assert_permission("viewer", Resource.ACTIVITY, Action.CREATE)


def test_permission_denied_error_message():
    try:
        assert_permission("viewer", Resource.ACTIVITY, Action.DELETE)
    except PermissionDeniedError as e:
        assert "viewer" in str(e)
        assert "delete" in str(e)
        assert "activity" in str(e)


# ── No viewer can write anything sensitive ────────────────────────────────────

@pytest.mark.parametrize("action", [
    Action.CREATE, Action.UPDATE, Action.DELETE, Action.APPROVE, Action.ADMIN,
])
def test_viewer_cannot_mutate(action):
    for resource in Resource:
        if resource in (Resource.PROJECT, Resource.ACTIVITY, Resource.RISK,
                        Resource.DRAWING, Resource.DOCUMENT, Resource.REPORT,
                        Resource.GRAPH):
            assert check_permission("viewer", resource, action) is False, \
                f"viewer should not have {action.value} on {resource.value}"


# ── vendor_portal cannot access internal data ────────────────────────────────

def test_vendor_portal_cannot_read_audit_log():
    assert check_permission("vendor_portal", Resource.AUDIT_LOG, Action.READ) is False


def test_vendor_portal_cannot_manage_users():
    assert check_permission("vendor_portal", Resource.USER, Action.CREATE) is False
    assert check_permission("vendor_portal", Resource.USER, Action.DELETE) is False
