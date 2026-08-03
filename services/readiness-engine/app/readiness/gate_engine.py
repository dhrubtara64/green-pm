"""Pure gate computation logic for the Readiness Engine — S10-02, S10-04."""
from __future__ import annotations

from datetime import date
from typing import Optional, Protocol

from app.readiness.schemas import (
    GateComputationResult,
    _GATE_TYPES,
)


class CriterionLike(Protocol):
    """Duck-typed protocol so the engine works with both ORM rows and test mocks."""

    status: str
    due_date: Optional[date]


def compute_gate_status(
    gate_type: str,
    criteria: list[CriterionLike],
    reference_date: Optional[date] = None,
) -> GateComputationResult:
    """Compute readiness status for a single gate from its criteria.

    Args:
        gate_type: One of the six gate type strings.
        criteria: All criteria linked to this gate.
        reference_date: Date used for overdue calculation. Defaults to today.

    Returns:
        Frozen GateComputationResult with status and completion percentage.
    """
    if gate_type not in _GATE_TYPES:
        raise ValueError(f"Unknown gate_type: {gate_type!r}")

    ref = reference_date or date.today()
    total = len(criteria)
    met = sum(1 for c in criteria if c.status == "MET")
    waived = sum(1 for c in criteria if c.status == "WAIVED")
    pending = sum(1 for c in criteria if c.status == "PENDING")

    if total == 0:
        pct = 100.0
    else:
        pct = round((met + waived) / total * 100, 2)

    if total == 0 or pct == 100.0:
        status = "READY" if total > 0 or met + waived == 0 else "READY"
    elif _has_overdue_pending(criteria, ref):
        status = "BLOCKED"
    elif met + waived == 0:
        status = "NOT_STARTED"
    else:
        status = "IN_PROGRESS"

    # Edge case: no criteria at all → READY
    if total == 0:
        status = "READY"

    return GateComputationResult(
        gate_type=gate_type,
        total_criteria=total,
        met_criteria=met,
        waived_criteria=waived,
        pending_criteria=pending,
        completion_percentage=pct,
        status=status,
    )


def identify_blocking_items(
    criteria: list[CriterionLike],
    reference_date: Optional[date] = None,
) -> list[CriterionLike]:
    """Return PENDING criteria whose due_date is past the reference date.

    A criterion without a due_date is never blocking.
    """
    ref = reference_date or date.today()
    return [
        c
        for c in criteria
        if c.status == "PENDING" and c.due_date is not None and c.due_date < ref
    ]


def _has_overdue_pending(
    criteria: list[CriterionLike],
    ref: date,
) -> bool:
    return any(
        c.status == "PENDING" and c.due_date is not None and c.due_date < ref
        for c in criteria
    )
