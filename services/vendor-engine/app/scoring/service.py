"""Vendor scoring service — persists scores and manages RFIs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import and_, select

from app.scoring.algorithm import compute_trend, compute_vendor_score
from app.scoring.model import RFI, VendorScoreRecord
from app.scoring.schemas import DimensionScores, ReliabilityPrediction

_RFI_STATUSES: frozenset[str] = frozenset({"OPEN", "RESPONDED", "CLOSED"})


class VendorScoreNotFoundError(Exception):
    pass


class InvalidRFIStatusError(Exception):
    pass


async def compute_and_store_score(
    session,
    tenant_id: uuid.UUID,
    vendor_id: uuid.UUID,
    project_id: uuid.UUID,
    dimension_scores: DimensionScores,
    weights: dict[str, float] | None = None,
    causal_attributions: list[dict] | None = None,
) -> VendorScoreRecord:
    """Compute vendor score and persist as a new VendorScoreRecord."""
    vendor_score = compute_vendor_score(vendor_id, dimension_scores, weights)

    record = VendorScoreRecord(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        project_id=project_id,
        tenant_id=tenant_id,
        dimension_scores=vendor_score.dimension_scores.as_dict(),
        overall_score=vendor_score.overall_score,
        weights=vendor_score.weights,
        causal_attributions=causal_attributions or [],
        computed_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def get_latest_score(
    session,
    tenant_id: uuid.UUID,
    vendor_id: uuid.UUID,
) -> Optional[VendorScoreRecord]:
    """Return the most recent VendorScoreRecord for this vendor, or None."""
    return await session.scalar(
        select(VendorScoreRecord)
        .where(
            and_(
                VendorScoreRecord.vendor_id == vendor_id,
                VendorScoreRecord.tenant_id == tenant_id,
            )
        )
        .order_by(VendorScoreRecord.computed_at.desc())
        .limit(1)
    )


async def get_score_history(
    session,
    tenant_id: uuid.UUID,
    vendor_id: uuid.UUID,
    limit: int = 20,
) -> list[VendorScoreRecord]:
    """Return up to `limit` score records, newest first."""
    result = await session.execute(
        select(VendorScoreRecord)
        .where(
            and_(
                VendorScoreRecord.vendor_id == vendor_id,
                VendorScoreRecord.tenant_id == tenant_id,
            )
        )
        .order_by(VendorScoreRecord.computed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_trend(
    session,
    tenant_id: uuid.UUID,
    vendor_id: uuid.UUID,
) -> ReliabilityPrediction:
    """Derive trend from stored score history (oldest-first)."""
    records = await get_score_history(session, tenant_id, vendor_id, limit=20)
    # score_history oldest first → reverse the newest-first list
    history = [r.overall_score for r in reversed(records)]
    return compute_trend(history)


async def create_rfi(
    session,
    tenant_id: uuid.UUID,
    vendor_id: uuid.UUID,
    project_id: uuid.UUID,
    rfi_number: str,
    title: str,
    description: str | None = None,
) -> RFI:
    """Create a new RFI in OPEN status."""
    rfi = RFI(
        id=uuid.uuid4(),
        vendor_id=vendor_id,
        project_id=project_id,
        tenant_id=tenant_id,
        rfi_number=rfi_number,
        title=title,
        description=description,
        status="OPEN",
        raised_at=datetime.now(timezone.utc),
    )
    session.add(rfi)
    await session.flush()
    return rfi


async def list_rfis(
    session,
    tenant_id: uuid.UUID,
    vendor_id: uuid.UUID,
    status: str | None = None,
) -> list[RFI]:
    """List RFIs for a vendor, optionally filtered by status."""
    if status is not None and status not in _RFI_STATUSES:
        raise InvalidRFIStatusError(
            f"Invalid RFI status filter {status!r}; must be one of {sorted(_RFI_STATUSES)}"
        )
    filters = [
        RFI.vendor_id == vendor_id,
        RFI.tenant_id == tenant_id,
    ]
    if status is not None:
        filters.append(RFI.status == status)

    result = await session.execute(
        select(RFI).where(and_(*filters)).order_by(RFI.raised_at.desc())
    )
    return list(result.scalars().all())
