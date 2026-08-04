"""SLO calculation and alert rule builder — S18-05."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ENGINE_NAMES: frozenset[str] = frozenset({
    "evidence-engine",
    "impact-engine",
    "dependency-engine",
    "supply-chain-engine",
    "vendor-engine",
    "risk-engine",
    "readiness-engine",
    "simulation-engine",
    "coordination-engine",
    "organizational-memory",
    "forecasting-engine",
    "alignment-engine",
    "decision-engine",
    "sync-engine",
    "pig-service",
    "core-platform",
    "recommendation-engine",
})

ENGINE_COUNT: int = 17
DEFAULT_LATENCY_THRESHOLD_MS: int = 800
DEFAULT_ERROR_RATE_THRESHOLD_PCT: float = 1.0
SLO_WINDOW_DAYS: int = 30


@dataclass(frozen=True)
class SLODefinition:
    engine_name: str
    latency_p99_ms: int
    error_rate_max_pct: float
    window_days: int = SLO_WINDOW_DAYS

    def __post_init__(self) -> None:
        if self.engine_name not in ENGINE_NAMES:
            raise ValueError(f"Unknown engine: '{self.engine_name}'")
        if self.latency_p99_ms < 1:
            raise ValueError("latency_p99_ms must be >= 1")
        if not (0.0 < self.error_rate_max_pct <= 100.0):
            raise ValueError("error_rate_max_pct must be in (0, 100]")

    @property
    def availability_target_pct(self) -> float:
        return 100.0 - self.error_rate_max_pct


@dataclass(frozen=True)
class AlertRule:
    engine_name: str
    metric: str
    threshold: float
    comparison: str
    duration_seconds: int
    severity: str

    def __post_init__(self) -> None:
        valid_comparisons = {"GREATER_THAN", "LESS_THAN", "GREATER_THAN_OR_EQUAL"}
        if self.comparison not in valid_comparisons:
            raise ValueError(f"comparison must be one of {valid_comparisons}")
        valid_severity = {"P1", "P2", "P3"}
        if self.severity not in valid_severity:
            raise ValueError(f"severity must be one of {valid_severity}")


def build_latency_alert(
    engine_name: str,
    threshold_ms: int = DEFAULT_LATENCY_THRESHOLD_MS,
    duration_seconds: int = 300,
) -> AlertRule:
    if engine_name not in ENGINE_NAMES:
        raise ValueError(f"Unknown engine: '{engine_name}'")
    return AlertRule(
        engine_name=engine_name,
        metric=f"custom.googleapis.com/{engine_name}/latency_p99",
        threshold=float(threshold_ms),
        comparison="GREATER_THAN",
        duration_seconds=duration_seconds,
        severity="P1",
    )


def build_error_rate_alert(
    engine_name: str,
    threshold_pct: float = DEFAULT_ERROR_RATE_THRESHOLD_PCT,
    duration_seconds: int = 60,
) -> AlertRule:
    if engine_name not in ENGINE_NAMES:
        raise ValueError(f"Unknown engine: '{engine_name}'")
    return AlertRule(
        engine_name=engine_name,
        metric=f"custom.googleapis.com/{engine_name}/error_rate",
        threshold=threshold_pct,
        comparison="GREATER_THAN",
        duration_seconds=duration_seconds,
        severity="P1",
    )


def slo_compliance(
    slo: SLODefinition, observed_p99_ms: float, observed_error_rate_pct: float
) -> dict:
    latency_ok = observed_p99_ms <= slo.latency_p99_ms
    error_ok = observed_error_rate_pct <= slo.error_rate_max_pct
    return {
        "engine": slo.engine_name,
        "latency_ok": latency_ok,
        "error_rate_ok": error_ok,
        "compliant": latency_ok and error_ok,
    }


def build_all_alert_rules() -> list[AlertRule]:
    rules = []
    for engine in sorted(ENGINE_NAMES):
        rules.append(build_latency_alert(engine))
        rules.append(build_error_rate_alert(engine))
    return rules
