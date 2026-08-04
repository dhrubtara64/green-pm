"""Service layer for Green PM Studio — S18-01."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.studio.model import StudioBuilder
from app.studio.registry import merge_config
from app.studio.schemas import BuilderCreate


class StudioBuilderNotFoundError(Exception):
    pass


async def create_builder(session, tenant_id: uuid.UUID, create: BuilderCreate) -> StudioBuilder:
    merged = merge_config(create.builder_type, create.config_data)
    record = StudioBuilder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        builder_type=create.builder_type,
        name=create.name,
        config_data=merged,
        description=create.description,
        is_active=True,
    )
    session.add(record)
    await session.flush()
    return record


async def get_builder(session, tenant_id: uuid.UUID, builder_id: uuid.UUID) -> StudioBuilder:
    record = await session.scalar(
        select(StudioBuilder).where(
            StudioBuilder.tenant_id == tenant_id,
            StudioBuilder.id == builder_id,
        )
    )
    if record is None:
        raise StudioBuilderNotFoundError(f"StudioBuilder {builder_id} not found")
    return record


async def list_builders(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    builder_type: str | None = None,
) -> list[StudioBuilder]:
    stmt = select(StudioBuilder).where(
        StudioBuilder.tenant_id == tenant_id,
        StudioBuilder.project_id == project_id,
    )
    if builder_type is not None:
        stmt = stmt.where(StudioBuilder.builder_type == builder_type)
    result = await session.execute(stmt)
    return list(result.scalars())


async def deactivate_builder(
    session, tenant_id: uuid.UUID, builder_id: uuid.UUID
) -> StudioBuilder:
    record = await get_builder(session, tenant_id, builder_id)
    record.is_active = False
    await session.flush()
    return record
