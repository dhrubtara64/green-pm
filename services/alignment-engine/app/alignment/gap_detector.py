"""Pure-function gap detection for the Alignment Engine — S14-05."""
from __future__ import annotations

from datetime import datetime

from app.alignment.schemas import (
    UNACKNOWLEDGED_SLA_HOURS,
    UNCONFIRMED_THRESHOLD_HOURS,
    AlignmentGapResult,
)

_SEVERITY_ORDER: dict[str, int] = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def score_gap_severity(gap_type: str, hours_overdue: float) -> str:
    """Return HIGH/MEDIUM/LOW based on how long overdue the gap is."""
    if hours_overdue > 48:
        return "HIGH"
    if hours_overdue > 24:
        return "MEDIUM"
    return "LOW"


def detect_gaps(
    receipts,
    now: datetime,
    unconfirmed_threshold_hours: float = UNCONFIRMED_THRESHOLD_HOURS,
    unacknowledged_sla_hours: float = UNACKNOWLEDGED_SLA_HOURS,
) -> list[AlignmentGapResult]:
    """Detect alignment gaps from a list of AlignmentReceipt ORM objects.

    Two gap types:
    - UNCONFIRMED_RECEIPT: sent_at > threshold hours ago with no receipt_confirmed_at
    - UNACKNOWLEDGED: receipt_confirmed_at > SLA hours ago with no acknowledgment_confirmed_at

    Returned list is sorted: HIGH first, then MEDIUM, then LOW; within same severity,
    highest hours_overdue first.
    """
    gaps: list[AlignmentGapResult] = []
    for r in receipts:
        if r.sent_at is None:
            continue
        sent_at = r.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=now.tzinfo)
        ref_now = now

        if r.receipt_confirmed_at is None:
            hours_since_sent = (ref_now - sent_at).total_seconds() / 3600
            if hours_since_sent > unconfirmed_threshold_hours:
                overdue = hours_since_sent - unconfirmed_threshold_hours
                gaps.append(
                    AlignmentGapResult(
                        receipt_id=r.id,
                        stakeholder_id=r.stakeholder_id,
                        event_type=r.event_type,
                        gap_type="UNCONFIRMED_RECEIPT",
                        severity=score_gap_severity("UNCONFIRMED_RECEIPT", overdue),
                        hours_overdue=round(overdue, 4),
                    )
                )
        elif r.acknowledgment_confirmed_at is None:
            receipt_at = r.receipt_confirmed_at
            if receipt_at.tzinfo is None:
                receipt_at = receipt_at.replace(tzinfo=now.tzinfo)
            hours_since_receipt = (ref_now - receipt_at).total_seconds() / 3600
            if hours_since_receipt > unacknowledged_sla_hours:
                overdue = hours_since_receipt - unacknowledged_sla_hours
                gaps.append(
                    AlignmentGapResult(
                        receipt_id=r.id,
                        stakeholder_id=r.stakeholder_id,
                        event_type=r.event_type,
                        gap_type="UNACKNOWLEDGED",
                        severity=score_gap_severity("UNACKNOWLEDGED", overdue),
                        hours_overdue=round(overdue, 4),
                    )
                )

    gaps.sort(key=lambda g: (_SEVERITY_ORDER[g.severity], -g.hours_overdue))
    return gaps
