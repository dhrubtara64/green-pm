"""Pipeline handler — change.initiated event → impact assessment — S5-03."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.outbox.writer import write_outbox_event

from ..changes.model import ImpactAssessment
from ..changes.service import get_change
from ..impact.service import quantify_impact
from ..traversal.pig_traversal import traverse_impact

_IMPACT_TOPIC = "greenpm.impact"


class InvalidChangePayloadError(Exception):
    pass


def parse_change_initiated_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and parse a change.initiated event payload.

    Raises InvalidChangePayloadError on missing required fields.
    """
    required = {"change_id", "project_id", "entity_type", "entity_id"}
    missing = required - payload.keys()
    if missing:
        raise InvalidChangePayloadError(
            f"Missing required fields in change.initiated payload: {sorted(missing)}"
        )
    return {
        "change_id": uuid.UUID(str(payload["change_id"])),
        "project_id": uuid.UUID(str(payload["project_id"])),
        "entity_type": str(payload["entity_type"]),
        "entity_id": uuid.UUID(str(payload["entity_id"])),
    }


async def handle_change_initiated(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
    *,
    max_hops: int = 5,
) -> ImpactAssessment:
    """End-to-end pipeline: parse → traverse → quantify → persist → emit.

    Completes within 10 seconds for typical project sizes.
    Caller owns the transaction boundary.
    """
    parsed = parse_change_initiated_payload(payload)
    change_id = parsed["change_id"]
    project_id = parsed["project_id"]
    entity_type = parsed["entity_type"]
    entity_id = parsed["entity_id"]

    change = await get_change(session, tenant_id, change_id)
    change.status = "assessing"
    await session.flush()

    traversal = await traverse_impact(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        start_entity_type=entity_type,
        start_entity_id=entity_id,
        max_hops=max_hops,
    )

    impact = quantify_impact(traversal)
    now = datetime.now(timezone.utc)

    assessment = ImpactAssessment(
        id=uuid.uuid4(),
        change_id=change_id,
        tenant_id=tenant_id,
        project_id=project_id,
        status="assessed",
        dimensions=impact.as_dict()["dimensions"],
        affected_entity_ids=[str(eid) for eid in traversal.affected_entity_ids],
        impact_graph_edges=list(impact.impact_graph_edges),
        narrative_summary=impact.narrative_summary,
        computed_at=now,
    )
    session.add(assessment)

    change.status = "assessed"
    await session.flush()

    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_IMPACT_TOPIC,
        event_type="ImpactAssessed",
        payload={
            "assessment_id": str(assessment.id),
            "change_id": str(change_id),
            "project_id": str(project_id),
            "affected_entity_count": impact.affected_entity_count,
        },
    )

    return assessment
