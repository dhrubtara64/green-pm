"""Organizational Alignment Engine service layer — S14-04, S14-05, S14-06."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.alignment.gap_detector import detect_gaps
from app.alignment.model import AlignmentReceipt
from app.alignment.schemas import (
    AlignmentGapResult,
    AlignmentMapResponse,
    AlignmentReceiptCreate,
    StakeholderAlignmentStatus,
)


class AlignmentReceiptNotFoundError(Exception):
    pass


async def record_information_sent(
    session,
    tenant_id: uuid.UUID,
    create: AlignmentReceiptCreate,
) -> AlignmentReceipt:
    receipt = AlignmentReceipt(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        stakeholder_id=create.stakeholder_id,
        event_id=create.event_id,
        event_type=create.event_type,
        sent_at=datetime.now(timezone.utc),
    )
    session.add(receipt)
    await session.flush()
    return receipt


async def confirm_receipt(
    session,
    tenant_id: uuid.UUID,
    receipt_id: uuid.UUID,
    confirmed_at: Optional[datetime] = None,
) -> AlignmentReceipt:
    stmt = select(AlignmentReceipt).where(
        AlignmentReceipt.tenant_id == tenant_id,
        AlignmentReceipt.id == receipt_id,
    )
    receipt = await session.scalar(stmt)
    if receipt is None:
        raise AlignmentReceiptNotFoundError(
            f"AlignmentReceipt {receipt_id} not found"
        )
    receipt.receipt_confirmed_at = confirmed_at or datetime.now(timezone.utc)
    await session.flush()
    return receipt


async def confirm_acknowledgment(
    session,
    tenant_id: uuid.UUID,
    receipt_id: uuid.UUID,
    acknowledged_at: Optional[datetime] = None,
) -> AlignmentReceipt:
    stmt = select(AlignmentReceipt).where(
        AlignmentReceipt.tenant_id == tenant_id,
        AlignmentReceipt.id == receipt_id,
    )
    receipt = await session.scalar(stmt)
    if receipt is None:
        raise AlignmentReceiptNotFoundError(
            f"AlignmentReceipt {receipt_id} not found"
        )
    receipt.acknowledgment_confirmed_at = acknowledged_at or datetime.now(timezone.utc)
    await session.flush()
    return receipt


async def list_alignment(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    stakeholder_id: Optional[uuid.UUID] = None,
) -> list[AlignmentReceipt]:
    stmt = select(AlignmentReceipt).where(
        AlignmentReceipt.tenant_id == tenant_id,
        AlignmentReceipt.project_id == project_id,
    )
    if stakeholder_id is not None:
        stmt = stmt.where(AlignmentReceipt.stakeholder_id == stakeholder_id)
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_alignment_gaps(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    now: Optional[datetime] = None,
) -> list[AlignmentGapResult]:
    receipts = await list_alignment(session, tenant_id, project_id)
    return detect_gaps(receipts, now or datetime.now(timezone.utc))


async def get_alignment_map(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> AlignmentMapResponse:
    receipts = await list_alignment(session, tenant_id, project_id)
    by_stakeholder: dict[uuid.UUID, list[AlignmentReceipt]] = {}
    for r in receipts:
        by_stakeholder.setdefault(r.stakeholder_id, []).append(r)

    statuses = []
    for sid, recs in by_stakeholder.items():
        confirmed = [r for r in recs if r.receipt_confirmed_at is not None]
        acked = [r for r in recs if r.acknowledgment_confirmed_at is not None]
        statuses.append(
            StakeholderAlignmentStatus(
                stakeholder_id=sid,
                total_events=len(recs),
                confirmed_receipts=len(confirmed),
                acknowledged=len(acked),
                pending_receipts=len(recs) - len(confirmed),
                pending_acknowledgments=len(confirmed) - len(acked),
            )
        )

    unconfirmed = sum(1 for r in receipts if r.receipt_confirmed_at is None)
    unacked = sum(
        1 for r in receipts
        if r.receipt_confirmed_at is not None and r.acknowledgment_confirmed_at is None
    )
    return AlignmentMapResponse(
        project_id=project_id,
        stakeholders=statuses,
        total_receipts=len(receipts),
        unconfirmed_count=unconfirmed,
        unacknowledged_count=unacked,
    )
