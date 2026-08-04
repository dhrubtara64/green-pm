"""Pure ranking functions for the Recommendation Engine — S16-01."""
from __future__ import annotations

from typing import Any

DEFAULT_TOP_N: int = 10
_EVIDENCE_BONUS_PER_ITEM: float = 0.02
_MAX_EVIDENCE_BONUS: float = 0.10


def rank_recommendations(
    recommendations: list[Any],
    top_n: int = DEFAULT_TOP_N,
) -> list[Any]:
    """Return up to top_n recommendations sorted by priority_score descending."""
    if top_n < 0:
        raise ValueError("top_n must be non-negative")
    sorted_recs = sorted(recommendations, key=lambda r: r.priority_score, reverse=True)
    return sorted_recs[:top_n]


def score_recommendation(
    base_score: float,
    evidence_count: int,
    engine_weight: float = 1.0,
) -> float:
    """Compute boosted priority score from base score, evidence density, and engine weight.

    Evidence bonus caps at _MAX_EVIDENCE_BONUS to prevent low-quality signals
    being elevated by bulk evidence. Clamped to [0.0, 1.0].
    """
    if not (0.0 <= base_score <= 1.0):
        raise ValueError(f"base_score must be in [0.0, 1.0], got {base_score}")
    if evidence_count < 0:
        raise ValueError("evidence_count cannot be negative")
    if engine_weight <= 0:
        raise ValueError("engine_weight must be positive")
    evidence_bonus = min(evidence_count * _EVIDENCE_BONUS_PER_ITEM, _MAX_EVIDENCE_BONUS)
    raw = base_score * engine_weight + evidence_bonus
    return min(raw, 1.0)


def filter_by_minimum_score(
    recommendations: list[Any],
    min_score: float,
) -> list[Any]:
    """Return only recommendations with priority_score >= min_score."""
    if not (0.0 <= min_score <= 1.0):
        raise ValueError(f"min_score must be in [0.0, 1.0], got {min_score}")
    return [r for r in recommendations if r.priority_score >= min_score]


def group_by_signal_type(recommendations: list[Any]) -> dict[str, list[Any]]:
    """Group recommendations by signal_type, preserving rank order within each group."""
    groups: dict[str, list[Any]] = {}
    for rec in recommendations:
        groups.setdefault(rec.signal_type, []).append(rec)
    return groups
