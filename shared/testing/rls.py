from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TENANT_ISOLATED_TABLES = [
    "users",
    "projects",
    "user_project_access",
    "graph_nodes",
    "graph_edges",
    "outbox_events",
    "idempotency_keys",
    "audit_logs",
]


async def assert_rls_isolation(
    session_a: AsyncSession,
    session_b: AsyncSession,
    table: str,
    tenant_a_id: str,
    tenant_b_id: str,
) -> None:
    """Assert that neither tenant's session can see the other's rows.

    Raises AssertionError with the offending table name if data leaks.
    This must pass for every tenant-isolated table before a PR is merged.
    """
    result = await session_a.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"),
        {"tid": tenant_b_id},
    )
    count_a_sees_b = result.scalar_one()
    assert count_a_sees_b == 0, (
        f"RLS VIOLATION in '{table}': "
        f"Tenant A session can see {count_a_sees_b} rows belonging to Tenant B"
    )

    result = await session_b.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"),
        {"tid": tenant_a_id},
    )
    count_b_sees_a = result.scalar_one()
    assert count_b_sees_a == 0, (
        f"RLS VIOLATION in '{table}': "
        f"Tenant B session can see {count_b_sees_a} rows belonging to Tenant A"
    )


async def assert_all_tables_isolated(
    session_a: AsyncSession,
    session_b: AsyncSession,
    tenant_a_id: str,
    tenant_b_id: str,
) -> None:
    """Run RLS isolation check across all Phase 0 tenant-isolated tables."""
    for table in TENANT_ISOLATED_TABLES:
        await assert_rls_isolation(
            session_a, session_b, table, tenant_a_id, tenant_b_id
        )
