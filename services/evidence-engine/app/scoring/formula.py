"""Evidence Score v5 formula — S3-05.

Pure deterministic function; no LLM, no I/O.

Formula:
  score = (min(source_count, 10) / 10 × 0.25)
        + (recency_decay_avg × 0.25)
        + (corroboration_ratio × 0.25)
        + (capture_diversity × 0.15)
        + (reliability_weight_avg × 0.10)

All components are in [0.0, 1.0]; score is clamped to [0.0, 1.0].
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

_CAPTURE_TYPE_COUNT = 12  # defined by the capture_type ENUM

_RELIABILITY_WEIGHTS: dict[str, float] = {
    "primary": 1.0,
    "secondary": 0.7,
    "tertiary": 0.2,
}

_30_DAYS_SECONDS: float = 30.0 * 86_400.0

_W_SOURCE    = 0.25
_W_RECENCY   = 0.25
_W_CORROBORATION = 0.25
_W_DIVERSITY = 0.15
_W_RELIABILITY = 0.10


@dataclass(frozen=True)
class EvidenceItem:
    """Minimal evidence descriptor needed for score computation."""
    captured_at: datetime
    capture_type: str
    reliability_tier: str


@dataclass(frozen=True)
class ComputedScore:
    score_value: float
    source_count: int
    recency_decay: float
    corroboration_ratio: float
    capture_diversity: float
    reliability_weight_avg: float


def _item_recency(item: EvidenceItem, now: datetime) -> float:
    """Linear decay: 1.0 today → 0.0 at 30 days or older."""
    captured = item.captured_at
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    age = (now - captured).total_seconds()
    return max(0.0, 1.0 - age / _30_DAYS_SECONDS)


def compute_evidence_score(
    items: Sequence[EvidenceItem],
    *,
    now: datetime,
    corroboration_ratio: float = 1.0,
) -> ComputedScore:
    """Compute Evidence Score v5 for a set of evidence items.

    Args:
        items: All active evidence items for the entity.
        now: Reference timestamp for recency decay (injected for testability).
        corroboration_ratio: Fraction of items that agree on current state.
                             Defaults to 1.0 (no contradictions detected).

    Returns:
        ComputedScore with all five components and the composite score.
    """
    if not items:
        return ComputedScore(
            score_value=0.0,
            source_count=0,
            recency_decay=0.0,
            corroboration_ratio=round(max(0.0, min(1.0, corroboration_ratio)), 3),
            capture_diversity=0.0,
            reliability_weight_avg=0.0,
        )

    source_count = len(items)

    # Source contribution (capped at 10)
    source_component = min(source_count, 10) / 10.0

    # Recency — average linear decay across all items
    recencies = [_item_recency(item, now) for item in items]
    recency_avg = sum(recencies) / len(recencies)

    # Corroboration — passed in by caller
    corroboration = max(0.0, min(1.0, corroboration_ratio))

    # Capture diversity — distinct types / 12
    distinct_types = len({item.capture_type for item in items})
    diversity = distinct_types / _CAPTURE_TYPE_COUNT

    # Reliability — weighted average of tier weights
    weights = [_RELIABILITY_WEIGHTS.get(item.reliability_tier, 0.2) for item in items]
    reliability_avg = sum(weights) / len(weights)

    # Composite
    score = (
        source_component  * _W_SOURCE
        + recency_avg     * _W_RECENCY
        + corroboration   * _W_CORROBORATION
        + diversity       * _W_DIVERSITY
        + reliability_avg * _W_RELIABILITY
    )
    score = max(0.0, min(1.0, score))

    return ComputedScore(
        score_value=round(score, 3),
        source_count=source_count,
        recency_decay=round(recency_avg, 3),
        corroboration_ratio=round(corroboration, 3),
        capture_diversity=round(diversity, 3),
        reliability_weight_avg=round(reliability_avg, 3),
    )
