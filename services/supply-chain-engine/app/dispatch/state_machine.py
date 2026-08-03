"""10-stage dispatch lifecycle state machine — sequential, no skipping."""
from __future__ import annotations

from app.dispatch.schemas import _DISPATCH_STAGES, _VALID_TRANSITIONS


class InvalidTransitionError(Exception):
    """Raised when a dispatch stage transition is not allowed."""


class DispatchStateMachine:
    """Validates and applies dispatch stage transitions.

    Only sequential forward transitions are permitted:
    PO_RAISED → VENDOR_CONFIRMED → … → ACCEPTED (terminal).
    """

    def validate_transition(self, current_stage: str, target_stage: str) -> None:
        """Raise InvalidTransitionError if target_stage is not the allowed next stage."""
        if current_stage not in _VALID_TRANSITIONS:
            raise InvalidTransitionError(
                f"Unknown dispatch stage: {current_stage!r}"
            )
        if target_stage not in _VALID_TRANSITIONS:
            raise InvalidTransitionError(
                f"Unknown target stage: {target_stage!r}"
            )
        allowed_next = _VALID_TRANSITIONS[current_stage]
        if allowed_next is None:
            raise InvalidTransitionError(
                f"{current_stage!r} is the terminal dispatch stage; no further transitions allowed"
            )
        if target_stage != allowed_next:
            raise InvalidTransitionError(
                f"Cannot transition from {current_stage!r} to {target_stage!r}; "
                f"only {allowed_next!r} is allowed next"
            )

    def next_stage(self, current_stage: str) -> str | None:
        """Return the next valid stage, or None if current_stage is terminal."""
        return _VALID_TRANSITIONS.get(current_stage)

    def is_terminal(self, stage: str) -> bool:
        """Return True if stage is the final stage (ACCEPTED)."""
        return _VALID_TRANSITIONS.get(stage) is None

    def stage_index(self, stage: str) -> int:
        """Return the 0-based index of stage in the lifecycle sequence."""
        return _DISPATCH_STAGES.index(stage)
