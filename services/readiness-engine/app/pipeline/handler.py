"""Event subscription handler for readiness gate recomputation — S10-06."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.readiness.service import list_gates, recompute_gate_score
from shared.outbox.writer import write_outbox_event

_READINESS_TOPIC: str = "greenpm.readiness"

_SUBSCRIBED_EVENTS: frozenset[str] = frozenset(
    {
        "supply.chain.readiness.updated",
        "activity.updated",
        "evidence.score.computed",
    }
)


class UnknownReadinessEventError(Exception):
    pass


class InvalidReadinessEventPayloadError(Exception):
    pass


def _validate_payload(payload: dict) -> tuple[uuid.UUID, uuid.UUID]:
    """Extract and validate tenant_id + project_id from event payload."""
    missing = [f for f in ("tenant_id", "project_id") if f not in payload or not payload[f]]
    if missing:
        raise InvalidReadinessEventPayloadError(
            f"Missing required fields: {missing}"
        )
    try:
        tenant_id = uuid.UUID(str(payload["tenant_id"]))
        project_id = uuid.UUID(str(payload["project_id"]))
    except (ValueError, AttributeError) as exc:
        raise InvalidReadinessEventPayloadError(f"Invalid UUID in payload: {exc}") from exc
    return tenant_id, project_id


async def handle_readiness_event(
    session: AsyncSession,
    payload: dict,
) -> int:
    """Recompute all gates for the project and emit a readiness update event.

    Returns the number of gates recomputed.
    """
    event_type = payload.get("event_type", "")
    if event_type not in _SUBSCRIBED_EVENTS:
        raise UnknownReadinessEventError(
            f"Unrecognised readiness event: {event_type!r}"
        )

    tenant_id, project_id = _validate_payload(payload)

    gates = await list_gates(session, tenant_id, project_id)
    for gate in gates:
        await recompute_gate_score(session, tenant_id, gate.id)

    write_outbox_event(
        session=session,
        topic=_READINESS_TOPIC,
        event_type="ReadinessGateUpdated",
        payload={
            "project_id": str(project_id),
            "tenant_id": str(tenant_id),
            "event_source": event_type,
            "gate_count": len(gates),
        },
    )
    return len(gates)
