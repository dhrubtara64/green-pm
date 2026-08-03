"""Activity service — CRUD + PIG registration + outbox events."""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.pig.sync import build_activity_attributes, sync_entity
from shared.outbox.writer import write_outbox_event

from .model import Activity
from .schemas import ActivityCreate, ActivityUpdate

_ACTIVITY_TOPIC = "greenpm.activities"


class ActivityNotFoundError(Exception):
    def __init__(self, activity_id: uuid.UUID) -> None:
        super().__init__(f"Activity {activity_id} not found")


async def create_activity(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: ActivityCreate,
) -> Activity:
    activity = Activity(
        id=uuid.uuid4(),
        project_id=data.project_id,
        tenant_id=tenant_id,
        name=data.name,
        wbs_code=data.wbs_code,
        status=data.status,
        progress_pct=data.progress_pct,
        planned_start=data.planned_start,
        planned_finish=data.planned_finish,
        pig_node_id=None,
    )
    session.add(activity)
    await session.flush()

    # Register in PIG within the same transaction
    node = await sync_entity(
        session,
        tenant_id=tenant_id,
        project_id=data.project_id,
        entity_type="activity",
        entity_id=activity.id,
        attributes=build_activity_attributes(activity),
    )
    activity.pig_node_id = node.id
    await session.flush()

    # Write outbox event (same transaction)
    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_ACTIVITY_TOPIC,
        event_type="ActivityCreated",
        payload={
            "activity_id": str(activity.id),
            "project_id": str(activity.project_id),
            "name": activity.name,
            "status": activity.status,
            "pig_node_id": str(node.id),
        },
    )
    await session.refresh(activity)
    return activity


async def get_activity(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> Activity:
    activity = await session.scalar(
        select(Activity).where(
            and_(Activity.id == activity_id, Activity.tenant_id == tenant_id)
        )
    )
    if activity is None:
        raise ActivityNotFoundError(activity_id)
    return activity


async def list_activities(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[Activity]:
    q = (
        select(Activity)
        .where(and_(Activity.project_id == project_id, Activity.tenant_id == tenant_id))
        .order_by(Activity.created_at.desc())
        .limit(limit).offset(offset)
    )
    if status is not None:
        q = q.where(Activity.status == status)
    result = await session.execute(q)
    return result.scalars().all()


async def update_activity(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    activity_id: uuid.UUID,
    data: ActivityUpdate,
) -> Activity:
    activity = await get_activity(session, tenant_id, activity_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)
    await session.flush()

    # Re-sync PIG node with updated attributes
    await sync_entity(
        session,
        tenant_id=tenant_id,
        project_id=activity.project_id,
        entity_type="activity",
        entity_id=activity.id,
        attributes=build_activity_attributes(activity),
    )

    # Write outbox event
    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_ACTIVITY_TOPIC,
        event_type="ActivityUpdated",
        payload={
            "activity_id": str(activity.id),
            "project_id": str(activity.project_id),
            "changes": list(update_data.keys()),
        },
    )
    await session.refresh(activity)
    return activity
