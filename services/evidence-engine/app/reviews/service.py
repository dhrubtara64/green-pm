"""Evidence Review service — S4-01 (workflow) + S4-05 (score recompute trigger)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.outbox.writer import write_outbox_event

from ..evidence.model import EvidenceReview
from ..evidence.service import EvidenceNotFoundError, compute_and_store_score, get_evidence
from .schemas import EvidenceReviewCreate

_REVIEW_OUTCOMES = frozenset({"approved", "rejected", "needs_revision"})
_REVIEWABLE_STATUSES = frozenset({"submitted", "under_review"})
_REVIEW_TOPIC = "greenpm.evidence"

# Evidence status after each review outcome
_OUTCOME_TO_STATUS: dict[str, str] = {
    "approved": "approved",
    "rejected": "rejected",
    "needs_revision": "under_review",
}


class EvidenceReviewError(Exception):
    """Raised when a review cannot be created due to invalid state."""


async def create_review(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    evidence_id: uuid.UUID,
    data: EvidenceReviewCreate,
) -> EvidenceReview:
    """Submit a review decision for a piece of evidence.

    Enforces: SUBMITTED | UNDER_REVIEW → APPROVED | REJECTED | UNDER_REVIEW.
    Triggers score recomputation on approved / rejected outcomes (S4-05).
    Does NOT commit — caller owns the transaction.
    """
    evidence = await get_evidence(session, tenant_id, evidence_id)

    if evidence.status not in _REVIEWABLE_STATUSES:
        raise EvidenceReviewError(
            f"Cannot review evidence with status {evidence.status!r}. "
            f"Must be one of: {sorted(_REVIEWABLE_STATUSES)}"
        )

    now = datetime.now(timezone.utc)
    review = EvidenceReview(
        id=uuid.uuid4(),
        evidence_id=evidence_id,
        tenant_id=tenant_id,
        reviewer_id=reviewer_id,
        outcome=data.outcome,
        comments=data.comments,
        reviewed_at=now,
        reliability_weight=Decimal(str(data.reliability_weight)),
        created_at=now,
    )
    session.add(review)

    # Transition evidence status
    evidence.status = _OUTCOME_TO_STATUS[data.outcome]
    await session.flush()

    # Emit outbox event
    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_REVIEW_TOPIC,
        event_type="EvidenceReviewed",
        payload={
            "evidence_id": str(evidence_id),
            "project_id": str(evidence.project_id),
            "outcome": data.outcome,
            "reviewer_id": str(reviewer_id),
        },
    )

    # Recompute score on terminal outcomes — S4-05
    if data.outcome in {"approved", "rejected"}:
        await compute_and_store_score(
            session,
            tenant_id,
            evidence.project_id,
            evidence.entity_type,
            evidence.entity_id,
        )

    return review


async def list_reviews(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> Sequence[EvidenceReview]:
    result = await session.execute(
        select(EvidenceReview).where(
            and_(
                EvidenceReview.evidence_id == evidence_id,
                EvidenceReview.tenant_id == tenant_id,
            )
        ).order_by(EvidenceReview.reviewed_at.desc())
    )
    return result.scalars().all()
