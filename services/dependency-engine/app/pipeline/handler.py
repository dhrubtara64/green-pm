"""Pipeline handler — processes activity.updated events and triggers CPM recompute."""
from __future__ import annotations

import uuid

from shared.outbox.writer import write_outbox_event
from app.cpm.model import CriticalPathResult
from app.cpm.service import run_cpm_for_project

_CPM_TOPIC = "greenpm.cpm"

_REQUIRED_FIELDS = frozenset({"project_id", "tenant_id"})


class InvalidActivityPayloadError(Exception):
    pass


def parse_activity_updated_payload(payload: dict) -> dict:
    """Parse and validate an activity.updated event payload.

    Returns a dict with project_id and tenant_id as UUIDs.
    Raises InvalidActivityPayloadError for missing or invalid fields.
    """
    if not payload:
        raise InvalidActivityPayloadError(
            "activity.updated payload is empty"
        )
    missing = _REQUIRED_FIELDS - payload.keys()
    if missing:
        raise InvalidActivityPayloadError(
            f"Missing required fields in activity.updated payload: {sorted(missing)}"
        )
    try:
        parsed: dict = {
            "project_id": uuid.UUID(str(payload["project_id"])),
            "tenant_id": uuid.UUID(str(payload["tenant_id"])),
        }
    except (ValueError, AttributeError) as exc:
        raise InvalidActivityPayloadError(
            f"Invalid UUID in activity.updated payload: {exc}"
        ) from exc

    if "activity_id" in payload:
        try:
            parsed["activity_id"] = uuid.UUID(str(payload["activity_id"]))
        except (ValueError, AttributeError):
            parsed["activity_id"] = None
    else:
        parsed["activity_id"] = None

    return parsed


async def handle_activity_updated(
    session,
    payload: dict,
) -> CriticalPathResult:
    """Trigger CPM recompute for the project in the activity.updated payload.

    Emits a critical.path.recomputed outbox event after computation.
    """
    parsed = parse_activity_updated_payload(payload)
    project_id = parsed["project_id"]
    tenant_id = parsed["tenant_id"]

    result = await run_cpm_for_project(session, tenant_id, project_id)

    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_CPM_TOPIC,
        event_type="CriticalPathRecomputed",
        payload={
            "result_id": str(result.id),
            "project_id": str(project_id),
            "project_duration": result.project_duration,
            "critical_path_length": len(result.critical_path_activity_ids),
            "near_critical_count": len(result.near_critical_activity_ids),
        },
    )
    return result
