"""PIG Sync — synchronizes domain entities into the Project Intelligence Graph.

Every service that mutates a tracked entity calls sync_entity() within the
same database transaction so the graph node is always consistent with the
entity row. The sync is synchronous (same transaction, same DB connection)
— never out-of-band — to guarantee the PIG never lags behind the source.

Entity types tracked here must match the 22-type ENUM in the migration.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.graph import GraphNode

_TRACKED_ENTITY_TYPES = frozenset({
    "activity", "milestone", "drawing", "document", "equipment",
    "vendor", "dispatch", "evidence", "change", "decision",
    "risk", "issue", "gate", "wbs", "package", "shipment",
    "claim", "payment", "inspection", "commissioning_item",
    "organizational_unit", "person",
})


class UntrackedEntityTypeError(Exception):
    def __init__(self, entity_type: str) -> None:
        super().__init__(
            f"Entity type {entity_type!r} is not tracked by the PIG. "
            f"Must be one of: {sorted(_TRACKED_ENTITY_TYPES)}"
        )


async def sync_entity(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    attributes: dict[str, Any],
) -> GraphNode:
    """Upsert a graph node for the given entity within the caller's transaction.

    This MUST be called inside an open transaction. It uses flush (not commit)
    so the caller controls the transaction boundary.
    """
    if entity_type not in _TRACKED_ENTITY_TYPES:
        raise UntrackedEntityTypeError(entity_type)

    from sqlalchemy import and_, select

    now = datetime.now(timezone.utc)
    existing = await session.scalar(
        select(GraphNode).where(
            and_(
                GraphNode.project_id == project_id,
                GraphNode.entity_type == entity_type,
                GraphNode.entity_id == entity_id,
                GraphNode.tenant_id == tenant_id,
            )
        )
    )
    if existing is not None:
        existing.attributes = attributes
        existing.last_synced_at = now
        await session.flush()
        return existing

    node = GraphNode(
        id=uuid.uuid4(),
        project_id=project_id,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        attributes=attributes,
        last_synced_at=now,
    )
    session.add(node)
    await session.flush()
    return node


def build_activity_attributes(activity: Any) -> dict[str, Any]:
    """Extract PIG-relevant attributes from an Activity ORM object."""
    return {
        "name": activity.name,
        "status": getattr(activity, "status", None),
        "progress_pct": getattr(activity, "progress_pct", None),
        "planned_start": _dt_iso(getattr(activity, "planned_start", None)),
        "planned_finish": _dt_iso(getattr(activity, "planned_finish", None)),
        "actual_start": _dt_iso(getattr(activity, "actual_start", None)),
        "actual_finish": _dt_iso(getattr(activity, "actual_finish", None)),
    }


def _dt_iso(dt: Any) -> Any:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)
