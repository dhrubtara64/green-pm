"""Change service — CRUD + outbox event emission — S5-05."""
from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.outbox.writer import write_outbox_event

from .model import Change
from .schemas import ChangeCreate

_CHANGE_TOPIC = "greenpm.changes"


class ChangeNotFoundError(Exception):
    def __init__(self, change_id: uuid.UUID) -> None:
        super().__init__(f"Change {change_id} not found")


async def create_change(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    data: ChangeCreate,
) -> Change:
    """Create a change record and emit ChangeInitiated outbox event.

    Caller owns the transaction boundary — does NOT commit.
    """
    change = Change(
        id=uuid.uuid4(),
        project_id=data.project_id,
        tenant_id=tenant_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        change_type=data.change_type,
        description=data.description,
        status="initiated",
        change_metadata=dict(data.metadata),
        created_by=created_by,
    )
    session.add(change)
    await session.flush()

    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_CHANGE_TOPIC,
        event_type="ChangeInitiated",
        payload={
            "change_id": str(change.id),
            "project_id": str(data.project_id),
            "entity_type": data.entity_type,
            "entity_id": str(data.entity_id),
            "change_type": data.change_type,
        },
    )
    return change


async def get_change(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    change_id: uuid.UUID,
) -> Change:
    ch = await session.scalar(
        select(Change).where(
            and_(Change.id == change_id, Change.tenant_id == tenant_id)
        )
    )
    if ch is None:
        raise ChangeNotFoundError(change_id)
    return ch


async def list_changes(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Change]:
    result = await session.execute(
        select(Change)
        .where(and_(Change.project_id == project_id, Change.tenant_id == tenant_id))
        .order_by(Change.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
