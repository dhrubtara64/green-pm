"""Domain schemas for vendor scoring, causal attribution, and reliability prediction."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Six scoring dimensions
_DIMENSIONS: tuple[str, ...] = (
    "quality",
    "delivery",
    "responsiveness",
    "documentation",
    "commercial",
    "relationship",
)

# Default weights — must sum to 1.0
_DEFAULT_WEIGHTS: dict[str, float] = {
    "quality": 0.25,
    "delivery": 0.25,
    "responsiveness": 0.15,
    "documentation": 0.10,
    "commercial": 0.15,
    "relationship": 0.10,
}

# Trend threshold — score-point change per period that signals a directional trend
_TREND_THRESHOLD: float = 2.0

# Valid trend directions
_TREND_DIRECTIONS: frozenset[str] = frozenset({"IMPROVING", "STABLE", "DECLINING"})


def _validate_score(value: float, name: str) -> float:
    if not (0.0 <= value <= 100.0):
        raise ValueError(f"Dimension score '{name}' must be in [0, 100]; got {value}")
    return value


@dataclass(frozen=True)
class DimensionScores:
    """Six independent 0–100 vendor performance scores."""
    quality: float
    delivery: float
    responsiveness: float
    documentation: float
    commercial: float
    relationship: float

    def __post_init__(self) -> None:
        for dim in _DIMENSIONS:
            _validate_score(object.__getattribute__(self, dim), dim)

    def as_dict(self) -> dict[str, float]:
        return {d: object.__getattribute__(self, d) for d in _DIMENSIONS}


@dataclass(frozen=True)
class VendorScore:
    """Result of a single vendor scoring computation."""
    vendor_id: uuid.UUID
    dimension_scores: DimensionScores
    overall_score: float       # 0–100, weighted average
    weights: dict[str, float]  # dimension → weight applied

    def as_dict(self) -> dict:
        return {
            "vendor_id": str(self.vendor_id),
            "dimension_scores": self.dimension_scores.as_dict(),
            "overall_score": self.overall_score,
            "weights": dict(self.weights),
        }


@dataclass(frozen=True)
class CausalAttribution:
    """Links a score change to the event that caused it."""
    event_type: str
    event_id: uuid.UUID
    dimension: str
    score_delta: float         # positive = improvement, negative = regression
    recorded_at: datetime


@dataclass(frozen=True)
class ReliabilityPrediction:
    """Trend analysis output for a vendor's score history."""
    direction: str             # IMPROVING | STABLE | DECLINING
    predicted_score_30d: float # extrapolated score 30 periods ahead
    rolling_window_size: int   # number of historical records used
    confidence: float          # 0.0–1.0; lower with few data points

    def __post_init__(self) -> None:
        if self.direction not in _TREND_DIRECTIONS:
            raise ValueError(
                f"direction must be one of {sorted(_TREND_DIRECTIONS)}; got {self.direction!r}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0, 1]; got {self.confidence}")
