"""Pure pattern-matching functions for Organizational Memory Engine — S13-05, S13-06."""
from __future__ import annotations
import uuid
from typing import Any

from app.memory.schemas import PatternMatch


def score_pattern_relevance(
    pattern_id: uuid.UUID,
    pattern_name: str,
    category: str,
    confidence_score: float,
    historical_outcomes: list,
    trigger_conditions: dict | None,
    query_keywords: list[str],
) -> float:
    """Return relevance score in [0.0, 1.0].

    Score = confidence_score × keyword_overlap_ratio.
    A pattern with no matching keywords scores 0.0.
    """
    if not query_keywords:
        return 0.0

    searchable: list[str] = [pattern_name.lower()]
    if trigger_conditions:
        for k, v in trigger_conditions.items():
            searchable.append(str(k).lower())
            searchable.append(str(v).lower())

    searchable_text = " ".join(searchable)
    matched = sum(1 for kw in query_keywords if kw.lower() in searchable_text)
    overlap_ratio = matched / len(query_keywords)
    return round(confidence_score * overlap_ratio, 4)


def find_matching_patterns(
    patterns: list[Any],
    query_keywords: list[str],
    category: str | None = None,
    top_k: int = 5,
) -> list[PatternMatch]:
    """Score all patterns against query_keywords, return top_k sorted by relevance desc.

    Each item in `patterns` must have: id, pattern_name, category,
    confidence_score, historical_outcomes, trigger_conditions.
    """
    scored: list[PatternMatch] = []
    for p in patterns:
        if category is not None and p.category != category:
            continue
        relevance = score_pattern_relevance(
            pattern_id=p.id,
            pattern_name=p.pattern_name,
            category=p.category,
            confidence_score=p.confidence_score,
            historical_outcomes=p.historical_outcomes or [],
            trigger_conditions=p.trigger_conditions,
            query_keywords=query_keywords,
        )
        if relevance > 0.0:
            scored.append(
                PatternMatch(
                    pattern_id=p.id,
                    pattern_name=p.pattern_name,
                    category=p.category,
                    confidence_score=p.confidence_score,
                    historical_outcomes=tuple(p.historical_outcomes or []),
                    relevance_score=relevance,
                )
            )
    scored.sort(key=lambda m: m.relevance_score, reverse=True)
    return scored[:top_k]
