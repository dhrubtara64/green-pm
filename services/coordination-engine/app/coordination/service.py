"""Coordination Engine service layer — S12-04, S12-05."""
from __future__ import annotations
import uuid
from datetime import date
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.coordination.model import CoordinationItem, CoordinationClosure
from app.coordination.pipeline_engine import InvalidTransitionError, validate_transition, record_stage_timestamp
from app.coordination.schemas import (
    CoordinationItemCreate,
    CoordinationSummaryResponse,
    _TERMINAL_STATUSES,
)


class CoordinationItemNotFoundError(Exception):
    pass


async def create_coordination_item(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    create: CoordinationItemCreate,
) -> CoordinationItem:
    item = CoordinationItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        title=create.title,
        description=create.description,
        status="OPEN",
        assignee_id=create.assignee_id,
        due_date=create.due_date,
        source_event_id=create.source_event_id,
        stage_timestamps={"OPEN": None},
    )
    session.add(item)
    await session.flush()
    return item


async def get_coordination_item(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
) -> CoordinationItem:
    result = await session.scalar(
        select(CoordinationItem).where(
            CoordinationItem.id == item_id,
            CoordinationItem.tenant_id == tenant_id,
        )
    )
    if result is None:
        raise CoordinationItemNotFoundError(f"CoordinationItem {item_id} not found")
    return result


async def list_coordination_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    status: Optional[str] = None,
    assignee_id: Optional[uuid.UUID] = None,
) -> list[CoordinationItem]:
    stmt = select(CoordinationItem).where(
        CoordinationItem.tenant_id == tenant_id,
        CoordinationItem.project_id == project_id,
    )
    if status is not None:
        stmt = stmt.where(CoordinationItem.status == status)
    if assignee_id is not None:
        stmt = stmt.where(CoordinationItem.assignee_id == assignee_id)
    rows = await session.execute(stmt)
    return list(rows.scalars())


async def transition_status(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    to_status: str,
    timestamp_iso: str = "",
) -> CoordinationItem:
    item = await get_coordination_item(session, tenant_id, item_id)
    validate_transition(item.status, to_status)
    item.status = to_status
    item.stage_timestamps = record_stage_timestamp(item.stage_timestamps, to_status, timestamp_iso)
    await session.flush()
    return item


async def close_item(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    closed_by: Optional[str] = None,
    resolution_notes: Optional[str] = None,
) -> CoordinationClosure:
    item = await get_coordination_item(session, tenant_id, item_id)
    closure = CoordinationClosure(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        coordination_item_id=item_id,
        project_id=item.project_id,
        closed_by=closed_by,
        resolution_notes=resolution_notes,
    )
    session.add(closure)
    await session.flush()
    return closure


async def get_overdue_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    reference_date: date,
) -> list[CoordinationItem]:
    rows = await session.execute(
        select(CoordinationItem).where(
            CoordinationItem.tenant_id == tenant_id,
            CoordinationItem.project_id == project_id,
        )
    )
    items = list(rows.scalars())
    return [
        item for item in items
        if item.due_date is not None
        and item.due_date < reference_date
        and item.status not in _TERMINAL_STATUSES
    ]


async def get_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    reference_date: date,
) -> CoordinationSummaryResponse:
    all_items = await list_coordination_items(session, tenant_id, project_id)
    overdue = await get_overdue_items(session, tenant_id, project_id, reference_date)
    by_status: dict[str, int] = {}
    for item in all_items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
    open_count = sum(
        1 for item in all_items if item.status not in _TERMINAL_STATUSES
    )
    return CoordinationSummaryResponse(
        total=len(all_items),
        open_count=open_count,
        overdue_count=len(overdue),
        by_status=by_status,
    )
