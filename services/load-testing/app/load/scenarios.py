"""Load test scenario definitions — S18-02."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

CONCURRENT_USERS_TARGET: int = 150
SUSTAIN_MINUTES: int = 30
MAX_ERROR_RATE_PCT: float = 0.1

SCENARIO_NAMES: frozenset[str] = frozenset({
    "PIG_QUERY",
    "EVIDENCE_SCORE",
    "FULL_PIPELINE",
    "COPILOT_QUERY",
    "RECOMMENDATION_LIST",
})

_SLO_THRESHOLDS_MS: dict[str, int] = {
    "PIG_QUERY": 800,
    "EVIDENCE_SCORE": 200,
    "FULL_PIPELINE": 30_000,
    "COPILOT_QUERY": 5_000,
    "RECOMMENDATION_LIST": 500,
}


@dataclass(frozen=True)
class LoadScenario:
    name: str
    concurrent_users: int
    sustain_minutes: int
    p99_threshold_ms: int
    ramp_up_seconds: int = 60
    error_rate_max_pct: float = MAX_ERROR_RATE_PCT

    def __post_init__(self) -> None:
        if self.name not in SCENARIO_NAMES:
            raise ValueError(f"Unknown scenario '{self.name}'")
        if self.concurrent_users < 1:
            raise ValueError("concurrent_users must be >= 1")
        if self.sustain_minutes < 1:
            raise ValueError("sustain_minutes must be >= 1")
        if self.p99_threshold_ms < 1:
            raise ValueError("p99_threshold_ms must be >= 1")
        if not (0.0 < self.error_rate_max_pct <= 100.0):
            raise ValueError("error_rate_max_pct must be in (0, 100]")

    @property
    def total_duration_seconds(self) -> int:
        return self.ramp_up_seconds + self.sustain_minutes * 60


def build_scenario(name: str, *, concurrent_users: int = CONCURRENT_USERS_TARGET) -> LoadScenario:
    if name not in SCENARIO_NAMES:
        raise ValueError(f"Unknown scenario '{name}'")
    return LoadScenario(
        name=name,
        concurrent_users=concurrent_users,
        sustain_minutes=SUSTAIN_MINUTES,
        p99_threshold_ms=_SLO_THRESHOLDS_MS[name],
    )


def build_standard_suite() -> list[LoadScenario]:
    return [build_scenario(name) for name in sorted(SCENARIO_NAMES)]


def scenario_summary(scenario: LoadScenario) -> dict:
    return {
        "name": scenario.name,
        "users": scenario.concurrent_users,
        "sustain_minutes": scenario.sustain_minutes,
        "p99_threshold_ms": scenario.p99_threshold_ms,
        "total_seconds": scenario.total_duration_seconds,
        "error_rate_max_pct": scenario.error_rate_max_pct,
    }
