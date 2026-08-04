"""Pipeline stage definitions for integration test harness — S18-03."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

PIPELINE_STAGES: tuple[str, ...] = (
    "EVIDENCE_INGESTION",
    "EVIDENCE_SCORING",
    "IMPACT_ANALYSIS",
    "DEPENDENCY_CHECK",
    "RISK_ASSESSMENT",
    "COORDINATION_LOOP",
    "CLOSE_LOOP",
)

STAGE_COUNT: int = len(PIPELINE_STAGES)
MAX_PIPELINE_SECONDS: int = 30

_STAGE_ORDER: dict[str, int] = {s: i for i, s in enumerate(PIPELINE_STAGES)}


@dataclass(frozen=True)
class PipelineStage:
    name: str
    timeout_seconds: int
    emits_event: bool
    required: bool = True

    def __post_init__(self) -> None:
        if self.name not in PIPELINE_STAGES:
            raise ValueError(f"Unknown stage '{self.name}'")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")

    @property
    def order(self) -> int:
        return _STAGE_ORDER[self.name]


_DEFAULT_STAGES: tuple[PipelineStage, ...] = (
    PipelineStage("EVIDENCE_INGESTION", timeout_seconds=5, emits_event=True),
    PipelineStage("EVIDENCE_SCORING", timeout_seconds=3, emits_event=True),
    PipelineStage("IMPACT_ANALYSIS", timeout_seconds=5, emits_event=True),
    PipelineStage("DEPENDENCY_CHECK", timeout_seconds=3, emits_event=True),
    PipelineStage("RISK_ASSESSMENT", timeout_seconds=5, emits_event=True),
    PipelineStage("COORDINATION_LOOP", timeout_seconds=5, emits_event=True),
    PipelineStage("CLOSE_LOOP", timeout_seconds=4, emits_event=True),
)


def get_default_stages() -> tuple[PipelineStage, ...]:
    return _DEFAULT_STAGES


def total_timeout(stages: tuple[PipelineStage, ...]) -> int:
    return sum(s.timeout_seconds for s in stages)


def stages_in_order(stages: tuple[PipelineStage, ...]) -> list[PipelineStage]:
    return sorted(stages, key=lambda s: s.order)


def validate_pipeline(stages: tuple[PipelineStage, ...]) -> list[str]:
    """Return list of validation errors; empty list means valid."""
    errors = []
    names = [s.name for s in stages_in_order(stages)]
    if total_timeout(stages) > MAX_PIPELINE_SECONDS:
        errors.append(
            f"Total timeout {total_timeout(stages)}s exceeds {MAX_PIPELINE_SECONDS}s"
        )
    required_missing = [
        s for s in PIPELINE_STAGES
        if s not in names and PipelineStage.__dataclass_fields__["required"].default
    ]
    return errors


def stage_by_name(name: str) -> PipelineStage:
    for stage in _DEFAULT_STAGES:
        if stage.name == name:
            return stage
    raise ValueError(f"Stage '{name}' not found")
