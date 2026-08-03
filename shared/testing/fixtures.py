from __future__ import annotations

import os
import uuid
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TENANT_A_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
TENANT_B_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")


def get_test_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://greenpm:devpassword@localhost:5432/greenpm_test",
    )


@pytest_asyncio.fixture(scope="session")
async def engine():
    url = get_test_db_url()
    _engine = create_async_engine(url, echo=False, pool_size=5)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Clean session with no tenant context — for migration/admin tests."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def tenant_a_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Session scoped to Tenant A via app.current_tenant_id."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(f"SET LOCAL app.current_tenant_id = '{TENANT_A_ID}'")
        )
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def tenant_b_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Session scoped to Tenant B via app.current_tenant_id."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(f"SET LOCAL app.current_tenant_id = '{TENANT_B_ID}'")
        )
        yield session
        await session.rollback()
