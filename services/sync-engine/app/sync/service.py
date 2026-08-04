"""Synchronization & Consistency Engine service layer — S15-06."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from app.sync.detector import detect_contradictions
from app.sync.model import SyncInconsistency
from app.sync.schemas import (
    INCONSISTENCY_THRESHOLD,
    ConsistencyReportResponse,
    InconsistencyResponse,
)


class InconsistencyNotFoundError(Exception):
    pass


async def run_consistency_check(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    edges: list[dict[str, Any]],
    threshold: float = INCONSISTENCY_THRESHOLD,
) -> list[SyncInconsistency]:
    contradictions = detect_contradictions(edges, threshold=threshold)
    now = datetime.now(timezone.utc)
    records: list[SyncInconsistency] = []
    for c in contradictions:
        record = SyncInconsistency(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            entity_a_id=c.entity_a_id,
            entity_b_id=c.entity_b_id,
            edge_type=c.edge_type,
            weight_a=c.weight_a,
            weight_b=c.weight_b,
            delta=c.delta,
            recommendation=c.recommendation,
            flagged_at=now,
        )
        session.add(record)
        records.append(record)
    if records:
        await session.flush()
    return records


async def resolve_inconsistency(
    session,
    tenant_id: uuid.UUID,
    inconsistency_id: uuid.UUID,
) -> SyncInconsistency:
    stmt = select(SyncInconsistency).where(
        SyncInconsistency.tenant_id == tenant_id,
        SyncInconsistency.id == inconsistency_id,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise InconsistencyNotFoundError(f"SyncInconsistency {inconsistency_id} not found")
    record.resolved_at = datetime.now(timezone.utc)
    await session.flush()
    return record


async def list_inconsistencies(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    resolved: bool = False,
) -> list[SyncInconsistency]:
    stmt = select(SyncInconsistency).where(
        SyncInconsistency.tenant_id == tenant_id,
        SyncInconsistency.project_id == project_id,
    )
    if not resolved:
        stmt = stmt.where(SyncInconsistency.resolved_at.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_consistency_report(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    edges: list[dict[str, Any]],
    threshold: float = INCONSISTENCY_THRESHOLD,
) -> ConsistencyReportResponse:
    contradictions = detect_contradictions(edges, threshold=threshold)
    inconsistency_responses = [
        InconsistencyResponse(
            id=uuid.uuid4(),
            entity_a_id=c.entity_a_id,
            entity_b_id=c.entity_b_id,
            edge_type=c.edge_type,
            weight_a=c.weight_a,
            weight_b=c.weight_b,
            delta=c.delta,
            recommendation=c.recommendation,
        )
        for c in contradictions
    ]
    return ConsistencyReportResponse(
        project_id=project_id,
        total_edges_checked=len(edges),
        inconsistencies_found=len(contradictions),
        inconsistencies=inconsistency_responses,
    )
