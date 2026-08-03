from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    EXPORT = "export"
    ADMIN = "admin"


class Resource(str, Enum):
    TENANT = "tenant"
    USER = "user"
    PROJECT = "project"
    ACTIVITY = "activity"
    EVIDENCE = "evidence"
    RISK = "risk"
    VENDOR = "vendor"
    DRAWING = "drawing"
    DOCUMENT = "document"
    REPORT = "report"
    AUDIT_LOG = "audit_log"
    GRAPH = "graph"


# Permission matrix: role -> set of (resource, action) tuples granted
# Roles inherit upward — each role lists ONLY its own grants.
# check_permission() resolves the full hierarchy.
_GRANTS: dict[str, FrozenSet[tuple[Resource, Action]]] = {
    "viewer": frozenset({
        (Resource.PROJECT, Action.READ),
        (Resource.ACTIVITY, Action.READ),
        (Resource.RISK, Action.READ),
        (Resource.DRAWING, Action.READ),
        (Resource.DOCUMENT, Action.READ),
        (Resource.REPORT, Action.READ),
        (Resource.GRAPH, Action.READ),
    }),
    "vendor_portal": frozenset({
        (Resource.PROJECT, Action.READ),
        (Resource.ACTIVITY, Action.READ),
        (Resource.VENDOR, Action.READ),
        (Resource.VENDOR, Action.UPDATE),
        (Resource.EVIDENCE, Action.CREATE),
        (Resource.EVIDENCE, Action.READ),
        (Resource.DOCUMENT, Action.READ),
    }),
    "engineer": frozenset({
        (Resource.PROJECT, Action.READ),
        (Resource.ACTIVITY, Action.CREATE),
        (Resource.ACTIVITY, Action.READ),
        (Resource.ACTIVITY, Action.UPDATE),
        (Resource.EVIDENCE, Action.CREATE),
        (Resource.EVIDENCE, Action.READ),
        (Resource.EVIDENCE, Action.UPDATE),
        (Resource.RISK, Action.CREATE),
        (Resource.RISK, Action.READ),
        (Resource.RISK, Action.UPDATE),
        (Resource.DRAWING, Action.READ),
        (Resource.DOCUMENT, Action.READ),
        (Resource.DOCUMENT, Action.CREATE),
        (Resource.GRAPH, Action.READ),
    }),
    "executive": frozenset({
        (Resource.PROJECT, Action.READ),
        (Resource.ACTIVITY, Action.READ),
        (Resource.EVIDENCE, Action.READ),
        (Resource.RISK, Action.READ),
        (Resource.VENDOR, Action.READ),
        (Resource.DRAWING, Action.READ),
        (Resource.DOCUMENT, Action.READ),
        (Resource.REPORT, Action.READ),
        (Resource.REPORT, Action.EXPORT),
        (Resource.GRAPH, Action.READ),
        (Resource.AUDIT_LOG, Action.READ),
    }),
    "project_manager": frozenset({
        (Resource.PROJECT, Action.READ),
        (Resource.PROJECT, Action.UPDATE),
        (Resource.ACTIVITY, Action.CREATE),
        (Resource.ACTIVITY, Action.READ),
        (Resource.ACTIVITY, Action.UPDATE),
        (Resource.ACTIVITY, Action.DELETE),
        (Resource.ACTIVITY, Action.APPROVE),
        (Resource.EVIDENCE, Action.CREATE),
        (Resource.EVIDENCE, Action.READ),
        (Resource.EVIDENCE, Action.UPDATE),
        (Resource.EVIDENCE, Action.DELETE),
        (Resource.EVIDENCE, Action.APPROVE),
        (Resource.RISK, Action.CREATE),
        (Resource.RISK, Action.READ),
        (Resource.RISK, Action.UPDATE),
        (Resource.RISK, Action.DELETE),
        (Resource.RISK, Action.APPROVE),
        (Resource.VENDOR, Action.READ),
        (Resource.VENDOR, Action.CREATE),
        (Resource.VENDOR, Action.UPDATE),
        (Resource.DRAWING, Action.CREATE),
        (Resource.DRAWING, Action.READ),
        (Resource.DRAWING, Action.UPDATE),
        (Resource.DOCUMENT, Action.CREATE),
        (Resource.DOCUMENT, Action.READ),
        (Resource.DOCUMENT, Action.UPDATE),
        (Resource.REPORT, Action.READ),
        (Resource.REPORT, Action.EXPORT),
        (Resource.GRAPH, Action.READ),
        (Resource.GRAPH, Action.UPDATE),
        (Resource.AUDIT_LOG, Action.READ),
        (Resource.USER, Action.READ),
    }),
    "tenant_admin": frozenset({
        (Resource.TENANT, Action.READ),
        (Resource.TENANT, Action.UPDATE),
        (Resource.USER, Action.CREATE),
        (Resource.USER, Action.READ),
        (Resource.USER, Action.UPDATE),
        (Resource.USER, Action.DELETE),
        (Resource.PROJECT, Action.CREATE),
        (Resource.PROJECT, Action.READ),
        (Resource.PROJECT, Action.UPDATE),
        (Resource.PROJECT, Action.DELETE),
        (Resource.REPORT, Action.READ),
        (Resource.REPORT, Action.EXPORT),
        (Resource.AUDIT_LOG, Action.READ),
    }),
    "super_admin": frozenset({
        (Resource.TENANT, Action.CREATE),
        (Resource.TENANT, Action.READ),
        (Resource.TENANT, Action.UPDATE),
        (Resource.TENANT, Action.DELETE),
        (Resource.TENANT, Action.ADMIN),
        (Resource.USER, Action.CREATE),
        (Resource.USER, Action.READ),
        (Resource.USER, Action.UPDATE),
        (Resource.USER, Action.DELETE),
        (Resource.USER, Action.ADMIN),
        (Resource.AUDIT_LOG, Action.READ),
        (Resource.AUDIT_LOG, Action.EXPORT),
    }),
}

# Grants are flat (not accumulated) — each role gets only what's explicitly listed.
# Roles are not a strict ladder: executive and engineer are separate tracks with
# different permissions. require_role() uses a separate rank order for seniority gates.

def check_permission(role: str, resource: Resource, action: Action) -> bool:
    """Return True if `role` is explicitly granted `action` on `resource`."""
    grants = _GRANTS.get(role)
    if grants is None:
        return False
    return (resource, action) in grants


class PermissionDeniedError(Exception):
    def __init__(self, role: str, resource: Resource, action: Action) -> None:
        super().__init__(
            f"Role {role!r} cannot perform {action.value!r} on {resource.value!r}"
        )


def assert_permission(role: str, resource: Resource, action: Action) -> None:
    if not check_permission(role, resource, action):
        raise PermissionDeniedError(role, resource, action)
