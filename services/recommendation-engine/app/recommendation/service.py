"""Recommendation Engine service layer — S16-01, S16-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.recommendation.model import Recommendation
from app.recommendation.ranker import DEFAULT_TOP_N, rank_recommendations
from app.recommendation.schemas import RecommendationCreate


class RecommendationNotFoundError(Exception):
    pass


async def create_recommendation(
    session,
    tenant_id: uuid.UUID,
    create: RecommendationCreate,
) -> Recommendation:
    record = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        engine_name=create.engine_name,
        signal_type=create.signal_type,
        priority_score=create.priority_score,
        title=create.title,
        description=create.description,
        projected_outcome=create.projected_outcome,
        responsible_party=create.responsible_party,
        evidence_ids=[str(eid) for eid in create.evidence_ids],
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def list_recommendations(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    status: Optional[str] = None,
    top_n: int = DEFAULT_TOP_N,
) -> list[Recommendation]:
    stmt = select(Recommendation).where(
        Recommendation.tenant_id == tenant_id,
        Recommendation.project_id == project_id,
    )
    if status is not None:
        stmt = stmt.where(Recommendation.status == status)
    result = await session.execute(stmt)
    all_recs = list(result.scalars())
    return rank_recommendations(all_recs, top_n=top_n)


async def get_recommendation(
    session,
    tenant_id: uuid.UUID,
    rec_id: uuid.UUID,
) -> Recommendation:
    stmt = select(Recommendation).where(
        Recommendation.tenant_id == tenant_id,
        Recommendation.id == rec_id,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise RecommendationNotFoundError(f"Recommendation {rec_id} not found")
    return record


async def update_recommendation_status(
    session,
    tenant_id: uuid.UUID,
    rec_id: uuid.UUID,
    new_status: str,
) -> Recommendation:
    record = await get_recommendation(session, tenant_id, rec_id)
    record.status = new_status
    await session.flush()
    return record
