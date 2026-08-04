"""SLO assertion functions for load test results — S18-02."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.load.scenarios import LoadScenario

PIG_QUERY_P99_MS: int = 800
EVIDENCE_SCORE_P99_MS: int = 200
MAX_ERROR_RATE_PCT: float = 0.1


@dataclass(frozen=True)
class SLOResult:
    scenario_name: str
    p99_ms: float
    error_rate_pct: float
    threshold_ms: int
    max_error_rate_pct: float

    @property
    def latency_passed(self) -> bool:
        return self.p99_ms <= self.threshold_ms

    @property
    def error_rate_passed(self) -> bool:
        return self.error_rate_pct <= self.max_error_rate_pct

    @property
    def passed(self) -> bool:
        return self.latency_passed and self.error_rate_passed

    @property
    def failure_reasons(self) -> list[str]:
        reasons = []
        if not self.latency_passed:
            reasons.append(
                f"P99 latency {self.p99_ms}ms exceeds threshold {self.threshold_ms}ms"
            )
        if not self.error_rate_passed:
            reasons.append(
                f"Error rate {self.error_rate_pct}% exceeds max {self.max_error_rate_pct}%"
            )
        return reasons


def assert_slo(scenario: LoadScenario, p99_ms: float, error_rate_pct: float) -> SLOResult:
    return SLOResult(
        scenario_name=scenario.name,
        p99_ms=p99_ms,
        error_rate_pct=error_rate_pct,
        threshold_ms=scenario.p99_threshold_ms,
        max_error_rate_pct=scenario.error_rate_max_pct,
    )


def assert_pig_query_slo(p99_ms: float) -> bool:
    return p99_ms <= PIG_QUERY_P99_MS


def assert_evidence_score_slo(p99_ms: float) -> bool:
    return p99_ms <= EVIDENCE_SCORE_P99_MS


def assert_error_rate(error_rate_pct: float) -> bool:
    if error_rate_pct < 0:
        raise ValueError("error_rate_pct must be >= 0")
    return error_rate_pct <= MAX_ERROR_RATE_PCT


def summarise_suite_results(results: list[SLOResult]) -> dict:
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    return {
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "all_passed": len(failed) == 0,
        "failures": [
            {"scenario": r.scenario_name, "reasons": r.failure_reasons}
            for r in failed
        ],
    }
