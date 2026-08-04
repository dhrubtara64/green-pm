"""7-stage coordination pipeline engine — S12-03."""
from __future__ import annotations
from app.coordination.schemas import _VALID_TRANSITIONS, _COORDINATION_STATUSES

PIPELINE_STAGES = (
    "Event",
    "Impact",
    "Action",
    "Notify",
    "Acknowledge",
    "Execute",
    "Verify",
    "Close",
)


class InvalidTransitionError(Exception):
    pass


def validate_transition(from_status: str, to_status: str) -> None:
    """Validate a status transition.

    Raises InvalidTransitionError for illegal skips or invalid statuses.
    Only sequential transitions are permitted: OPEN→ACKNOWLEDGED→EXECUTING→VERIFIED→CLOSED.
    """
    if from_status not in _COORDINATION_STATUSES:
        raise InvalidTransitionError(f"Unknown from_status: {from_status!r}")
    if to_status not in _COORDINATION_STATUSES:
        raise InvalidTransitionError(f"Unknown to_status: {to_status!r}")
    allowed = _VALID_TRANSITIONS.get(from_status)
    if allowed != to_status:
        raise InvalidTransitionError(
            f"Invalid transition: {from_status!r} → {to_status!r}. "
            f"Only {from_status!r} → {allowed!r} is permitted from this state."
        )


def record_stage_timestamp(
    stage_timestamps: dict | None,
    to_status: str,
    timestamp_iso: str,
) -> dict:
    """Return a new stage_timestamps dict with the transition timestamp recorded."""
    result = dict(stage_timestamps) if stage_timestamps else {}
    result[to_status] = timestamp_iso
    return result
