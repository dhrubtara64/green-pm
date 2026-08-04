"""Organizational Memory Engine service layer — S13-02–S13-06."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.model import MemoryContribution, MemoryPattern, MemoryRecord
from app.memory.pattern_matcher import find_matching_patterns
from app.memory.schemas import (
    HistoricalContextResponse,
    MemoryRecordCreate,
    MemorySearchResponse,
    PatternMatch,
)


class MemoryRecordNotFoundError(Exception):
    pass


async def record_memory(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    create: MemoryRecordCreate,
) -> MemoryRecord:
    record = MemoryRecord(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=create.project_id,
        category=create.category,
        summary=create.summary,
        entity_id=create.entity_id,
        entity_type=create.entity_type,
        context=create.context,
        confidence_score=create.confidence_score,
        outcome=create.outcome,
        created_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def get_memory_record(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    record_id: uuid.UUID,
) -> MemoryRecord:
    result = await session.scalar(
        select(MemoryRecord).where(
            MemoryRecord.id == record_id,
            MemoryRecord.tenant_id == tenant_id,
        )
    )
    if result is None:
        raise MemoryRecordNotFoundError(f"MemoryRecord {record_id} not found")
    return result


async def list_memory_records(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    category: Optional[str] = None,
) -> list[MemoryRecord]:
    stmt = select(MemoryRecord).where(
        MemoryRecord.tenant_id == tenant_id,
        MemoryRecord.project_id == project_id,
    )
    if category is not None:
        stmt = stmt.where(MemoryRecord.category == category)
    rows = await session.execute(stmt)
    return list(rows.scalars())


async def upsert_pattern(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    category: str,
    pattern_name: str,
    trigger_conditions: Optional[dict],
    historical_outcome: str,
    confidence_score: float,
) -> MemoryPattern:
    existing = await session.scalar(
        select(MemoryPattern).where(
            MemoryPattern.tenant_id == tenant_id,
            MemoryPattern.project_id == project_id,
            MemoryPattern.category == category,
            MemoryPattern.pattern_name == pattern_name,
        )
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing_outcomes: list = list(existing.historical_outcomes or [])
        if historical_outcome and historical_outcome not in existing_outcomes:
            existing_outcomes.append(historical_outcome)
        existing.historical_outcomes = existing_outcomes
        existing.occurrence_count = existing.occurrence_count + 1
        existing.confidence_score = round(
            (existing.confidence_score + confidence_score) / 2, 4
        )
        existing.updated_at = now
        await session.flush()
        return existing

    pattern = MemoryPattern(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        category=category,
        pattern_name=pattern_name,
        trigger_conditions=trigger_conditions,
        historical_outcomes=[historical_outcome] if historical_outcome else [],
        confidence_score=confidence_score,
        occurrence_count=1,
        created_at=now,
        updated_at=now,
    )
    session.add(pattern)
    await session.flush()
    return pattern


async def list_patterns(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    category: Optional[str] = None,
) -> list[MemoryPattern]:
    stmt = select(MemoryPattern).where(MemoryPattern.tenant_id == tenant_id)
    if project_id is not None:
        stmt = stmt.where(MemoryPattern.project_id == project_id)
    if category is not None:
        stmt = stmt.where(MemoryPattern.category == category)
    rows = await session.execute(stmt)
    return list(rows.scalars())


async def search_patterns(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_keywords: list[str],
    category: Optional[str] = None,
    top_k: int = 5,
) -> list[PatternMatch]:
    all_patterns = await list_patterns(session, tenant_id, project_id=project_id)
    return find_matching_patterns(all_patterns, query_keywords, category=category, top_k=top_k)


async def get_historical_context(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    category: str,
    context_keywords: list[str],
    top_k: int = 3,
) -> list[HistoricalContextResponse]:
    matches = await search_patterns(
        session, tenant_id, project_id,
        query_keywords=context_keywords,
        category=category,
        top_k=top_k,
    )
    return [
        HistoricalContextResponse(
            pattern_name=m.pattern_name,
            category=m.category,
            confidence_score=m.confidence_score,
            historical_outcomes=list(m.historical_outcomes),
            relevance_score=m.relevance_score,
        )
        for m in matches
    ]
