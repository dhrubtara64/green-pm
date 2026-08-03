from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.tenant import Tenant

from .schemas import TenantCreate, TenantUpdate


class TenantNotFoundError(Exception):
    def __init__(self, tenant_id: uuid.UUID) -> None:
        super().__init__(f"Tenant {tenant_id} not found")


class TenantNameConflictError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Tenant name already exists: {name!r}")


async def create_tenant(session: AsyncSession, data: TenantCreate) -> Tenant:
    existing = await session.scalar(
        select(Tenant).where(Tenant.name == data.name)
    )
    if existing is not None:
        raise TenantNameConflictError(data.name)

    tenant = Tenant(
        id=uuid.uuid4(),
        name=data.name,
        plan=data.plan,
        domain=data.domain,
        is_active=True,
    )
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)
    return tenant


async def get_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise TenantNotFoundError(tenant_id)
    return tenant


async def list_tenants(
    session: AsyncSession,
    *,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Tenant]:
    query = select(Tenant).order_by(Tenant.created_at.desc()).limit(limit).offset(offset)
    if is_active is not None:
        query = query.where(Tenant.is_active == is_active)
    result = await session.execute(query)
    return result.scalars().all()


async def update_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: TenantUpdate,
) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] != tenant.name:
        existing = await session.scalar(
            select(Tenant).where(Tenant.name == update_data["name"])
        )
        if existing is not None:
            raise TenantNameConflictError(update_data["name"])

    for field, value in update_data.items():
        setattr(tenant, field, value)

    await session.flush()
    await session.refresh(tenant)
    return tenant


async def deactivate_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    tenant.is_active = False
    await session.flush()
    await session.refresh(tenant)
    return tenant
