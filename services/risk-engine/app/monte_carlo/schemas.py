"""Frozen dataclasses for Monte Carlo simulation inputs and outputs — S9-02."""
from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_ITERATIONS: int = 10_000


@dataclass(frozen=True)
class MonteCarloInput:
    """Parameters for a single Monte Carlo risk simulation."""

    base_schedule: float
    schedule_std_dev: float
    base_cost: float
    cost_std_dev: float
    iterations: int = _DEFAULT_ITERATIONS

    def __post_init__(self) -> None:
        if self.iterations < 1:
            raise ValueError(f"iterations must be >= 1, got {self.iterations}")
        if self.schedule_std_dev < 0:
            raise ValueError(f"schedule_std_dev must be >= 0, got {self.schedule_std_dev}")
        if self.cost_std_dev < 0:
            raise ValueError(f"cost_std_dev must be >= 0, got {self.cost_std_dev}")


@dataclass(frozen=True)
class PercentileResult:
    """P10 / P50 / P80 output for one simulation dimension."""

    p10: float
    p50: float
    p80: float

    def __post_init__(self) -> None:
        if not (self.p10 <= self.p50 <= self.p80):
            raise ValueError(
                f"Percentiles must satisfy p10 <= p50 <= p80; "
                f"got p10={self.p10}, p50={self.p50}, p80={self.p80}"
            )

    def as_dict(self) -> dict[str, float]:
        return {"p10": self.p10, "p50": self.p50, "p80": self.p80}


@dataclass(frozen=True)
class MonteCarloResult:
    """Complete Monte Carlo simulation result for schedule and cost dimensions."""

    iterations: int
    schedule: PercentileResult
    cost: PercentileResult

    def as_dict(self) -> dict:
        return {
            "iterations": self.iterations,
            "schedule": self.schedule.as_dict(),
            "cost": self.cost.as_dict(),
        }
