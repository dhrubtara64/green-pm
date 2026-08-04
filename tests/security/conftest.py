"""Security test fixtures — RLS integration tests require `make dev` (PostgreSQL running)."""
import os
import uuid
import asyncio
import pytest

try:
    import asyncpg
    _ASYNCPG_AVAILABLE = True
except ModuleNotFoundError:
    asyncpg = None  # type: ignore[assignment]
    _ASYNCPG_AVAILABLE = False

_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://greenpm:devpassword@localhost:5432/greenpm",
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "rls: RLS cross-tenant isolation tests — require `make dev`"
    )


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def pg():
    """Raw asyncpg connection to PostgreSQL. Skips the entire session if unavailable."""
    if not _ASYNCPG_AVAILABLE:
        pytest.skip("asyncpg not installed — activate a service virtualenv or `pip install asyncpg`")
        return
    try:
        conn = await asyncpg.connect(_DATABASE_URL, timeout=3)
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable ({exc!s}) — run `make dev` first")
        return
    yield conn
    await conn.close()


@pytest.fixture(scope="session")
async def tenant_a_id(pg) -> uuid.UUID:
    """Insert tenant A and return its UUID. Cleaned up after session."""
    tid = uuid.uuid4()
    await pg.execute(
        "INSERT INTO tenants (id, name, plan) VALUES ($1, $2, 'pilot')",
        tid, f"test-rls-tenant-a-{tid.hex[:8]}",
    )
    yield tid
    await pg.execute("DELETE FROM tenants WHERE id = $1", tid)


@pytest.fixture(scope="session")
async def tenant_b_id(pg) -> uuid.UUID:
    """Insert tenant B and return its UUID. Cleaned up after session."""
    tid = uuid.uuid4()
    await pg.execute(
        "INSERT INTO tenants (id, name, plan) VALUES ($1, $2, 'pilot')",
        tid, f"test-rls-tenant-b-{tid.hex[:8]}",
    )
    yield tid
    await pg.execute("DELETE FROM tenants WHERE id = $1", tid)
