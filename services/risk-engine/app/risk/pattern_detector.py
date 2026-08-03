"""Risk pattern detection against organisational memory — S9-03."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.risk.model import MemoryPattern
from app.risk.schemas import RiskPatternMatch


async def detect_risk_patterns(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    risk_category: str,
    risk_description: str,
) -> list[RiskPatternMatch]:
    """Match current risk against stored organisational memory patterns.

    Confidence is derived from keyword overlap: matched_keywords / total_keywords,
    scaled by the pattern's confidence_base, capped at 1.0.
    Patterns with zero keyword overlap are excluded from results.
    """
    rows = await session.execute(
        select(MemoryPattern).where(MemoryPattern.tenant_id == tenant_id)
    )
    patterns = list(rows.scalars())

    combined_text = f"{risk_category} {risk_description}".lower()
    matches: list[RiskPatternMatch] = []

    for pattern in patterns:
        keywords: list[str] = pattern.keywords or []
        if not keywords:
            continue

        matched = sum(1 for kw in keywords if kw.lower() in combined_text)
        if matched == 0:
            continue

        raw_confidence = matched / len(keywords)
        confidence = round(min(1.0, raw_confidence * pattern.confidence_base * 2), 4)

        matches.append(
            RiskPatternMatch(
                pattern_id=pattern.id,
                pattern_name=pattern.pattern_name,
                confidence=confidence,
                historical_outcome=pattern.historical_outcome,
            )
        )

    return sorted(matches, key=lambda m: m.confidence, reverse=True)
