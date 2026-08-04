"""Decision Engine — 10-state lifecycle state machine — S15-02."""
from __future__ import annotations

_DECISION_STATES: frozenset[str] = frozenset({
    "DRAFT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "AWAITING_INPUT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "DEFERRED",
    "SUPERSEDED",
    "ARCHIVED",
})

_TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT":             frozenset({"SUBMITTED", "ARCHIVED"}),
    "SUBMITTED":         frozenset({"UNDER_REVIEW", "DRAFT"}),
    "UNDER_REVIEW":      frozenset({"AWAITING_INPUT", "PENDING_APPROVAL", "REJECTED", "DEFERRED"}),
    "AWAITING_INPUT":    frozenset({"UNDER_REVIEW"}),
    "PENDING_APPROVAL":  frozenset({"APPROVED", "REJECTED", "DEFERRED"}),
    "APPROVED":          frozenset({"SUPERSEDED", "ARCHIVED"}),
    "REJECTED":          frozenset({"ARCHIVED", "DRAFT"}),
    "DEFERRED":          frozenset({"UNDER_REVIEW", "ARCHIVED"}),
    "SUPERSEDED":        frozenset({"ARCHIVED"}),
    "ARCHIVED":          frozenset(),
}

_TERMINAL_STATES: frozenset[str] = frozenset({"ARCHIVED"})
_APPROVAL_GATE_STATES: frozenset[str] = frozenset({"APPROVED"})


def is_valid_transition(from_state: str, to_state: str) -> bool:
    return to_state in _TRANSITIONS.get(from_state, frozenset())


def get_valid_transitions(state: str) -> frozenset[str]:
    return _TRANSITIONS.get(state, frozenset())


def is_terminal(state: str) -> bool:
    return state in _TERMINAL_STATES


def requires_approval_gate(to_state: str) -> bool:
    return to_state in _APPROVAL_GATE_STATES


def required_approval_count(impact_level: str, approval_required: bool) -> int:
    if not approval_required:
        return 0
    return 2 if impact_level == "HIGH" else 1
