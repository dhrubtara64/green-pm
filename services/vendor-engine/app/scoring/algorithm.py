"""Pure vendor scoring algorithms — S8-01, S8-02, S8-03."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from app.scoring.schemas import (
    _DEFAULT_WEIGHTS,
    _DIMENSIONS,
    _TREND_THRESHOLD,
    CausalAttribution,
    DimensionScores,
    ReliabilityPrediction,
    VendorScore,
)


def compute_vendor_score(
    vendor_id: uuid.UUID,
    dimension_scores: DimensionScores,
    weights: dict[str, float] | None = None,
) -> VendorScore:
    """Compute the weighted-average overall vendor score.

    Weights default to _DEFAULT_WEIGHTS. Custom weights must cover all six
    dimensions and must sum to 1.0 (±0.01 tolerance).
    """
    if weights is None:
        weights = _DEFAULT_WEIGHTS

    total_weight = sum(weights.get(d, 0.0) for d in _DIMENSIONS)
    if abs(total_weight - 1.0) > 0.01:
        raise ValueError(
            f"Dimension weights must sum to 1.0 (±0.01); got {total_weight:.4f}"
        )

    overall = sum(
        object.__getattribute__(dimension_scores, dim) * weights.get(dim, 0.0)
        for dim in _DIMENSIONS
    )
    return VendorScore(
        vendor_id=vendor_id,
        dimension_scores=dimension_scores,
        overall_score=round(overall, 2),
        weights=dict(weights),
    )


def build_causal_attribution(
    event_type: str,
    event_id: uuid.UUID,
    dimension: str,
    old_score: float,
    new_score: float,
    recorded_at: datetime | None = None,
) -> CausalAttribution:
    """Create a causal attribution linking an event to a score dimension change."""
    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)
    return CausalAttribution(
        event_type=event_type,
        event_id=event_id,
        dimension=dimension,
        score_delta=round(new_score - old_score, 4),
        recorded_at=recorded_at,
    )


def compute_trend(score_history: Sequence[float]) -> ReliabilityPrediction:
    """Analyse a sequence of historical overall scores (oldest first) to produce
    a reliability prediction.

    With < 2 data points, direction is STABLE and confidence is 0.0.
    Direction is determined by slope per period:
        slope >= _TREND_THRESHOLD  → IMPROVING
        slope <= -_TREND_THRESHOLD → DECLINING
        otherwise                  → STABLE
    30-day prediction extrapolates from the last score by 30 * slope, capped to [0, 100].
    Confidence scales with window size up to a maximum of 1.0 at 10+ points.
    """
    n = len(score_history)

    if n < 2:
        last = float(score_history[0]) if n == 1 else 50.0
        return ReliabilityPrediction(
            direction="STABLE",
            predicted_score_30d=round(last, 2),
            rolling_window_size=n,
            confidence=0.0,
        )

    # Slope = average change per period over the full window
    slope = (score_history[-1] - score_history[0]) / (n - 1)

    if slope >= _TREND_THRESHOLD:
        direction = "IMPROVING"
    elif slope <= -_TREND_THRESHOLD:
        direction = "DECLINING"
    else:
        direction = "STABLE"

    predicted = round(min(100.0, max(0.0, score_history[-1] + slope * 30)), 2)
    confidence = round(min(1.0, n / 10), 2)

    return ReliabilityPrediction(
        direction=direction,
        predicted_score_30d=predicted,
        rolling_window_size=n,
        confidence=confidence,
    )
