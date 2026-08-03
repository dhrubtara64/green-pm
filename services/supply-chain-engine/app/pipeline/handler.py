"""Pipeline handler — processes stage transition events and emits readiness updates."""
from __future__ import annotations

import uuid

from shared.outbox.writer import write_outbox_event
from app.dispatch.model import Dispatch
from app.dispatch.service import transition_dispatch_stage

_SUPPLY_TOPIC = "greenpm.supply"

_REQUIRED_FIELDS = frozenset({"dispatch_id", "tenant_id", "project_id", "target_stage"})


class InvalidStageTransitionPayloadError(Exception):
    pass


def parse_stage_transition_payload(payload: dict) -> dict:
    """Parse and validate a stage transition event payload.

    Returns a dict with dispatch_id, tenant_id, project_id as UUIDs and target_stage as str.
    Raises InvalidStageTransitionPayloadError for missing or invalid fields.
    """
    if not payload:
        raise InvalidStageTransitionPayloadError("Stage transition payload is empty")

    missing = _REQUIRED_FIELDS - payload.keys()
    if missing:
        raise InvalidStageTransitionPayloadError(
            f"Missing required fields in stage transition payload: {sorted(missing)}"
        )

    try:
        return {
            "dispatch_id": uuid.UUID(str(payload["dispatch_id"])),
            "tenant_id": uuid.UUID(str(payload["tenant_id"])),
            "project_id": uuid.UUID(str(payload["project_id"])),
            "target_stage": str(payload["target_stage"]),
        }
    except (ValueError, AttributeError) as exc:
        raise InvalidStageTransitionPayloadError(
            f"Invalid field value in stage transition payload: {exc}"
        ) from exc


async def handle_stage_transition(
    session,
    payload: dict,
) -> Dispatch:
    """Transition a dispatch stage and emit supply.chain.readiness.updated outbox event."""
    parsed = parse_stage_transition_payload(payload)
    dispatch_id = parsed["dispatch_id"]
    tenant_id = parsed["tenant_id"]
    project_id = parsed["project_id"]
    target_stage = parsed["target_stage"]

    dispatch = await transition_dispatch_stage(session, tenant_id, dispatch_id, target_stage)

    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_SUPPLY_TOPIC,
        event_type="SupplyChainReadinessUpdated",
        payload={
            "dispatch_id": str(dispatch_id),
            "project_id": str(project_id),
            "new_stage": dispatch.current_stage,
            "material_readiness_score": dispatch.material_readiness_score,
            "critical_material_count": dispatch.critical_material_count,
        },
    )
    return dispatch
