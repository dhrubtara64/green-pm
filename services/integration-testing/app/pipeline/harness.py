"""Integration test harness — pure logic, no IO — S18-03."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.pipeline.stages import (
    PIPELINE_STAGES,
    MAX_PIPELINE_SECONDS,
    PipelineStage,
    get_default_stages,
    stages_in_order,
    total_timeout,
)

DLQ_THRESHOLD: int = 0


@dataclass
class StageResult:
    stage_name: str
    success: bool
    duration_seconds: float
    event_emitted: bool
    error_message: Optional[str] = None


@dataclass
class PipelineRun:
    results: list[StageResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.success for r in self.results)

    @property
    def total_duration(self) -> float:
        return sum(r.duration_seconds for r in self.results)

    @property
    def within_time_limit(self) -> bool:
        return self.total_duration <= MAX_PIPELINE_SECONDS

    @property
    def all_events_emitted(self) -> bool:
        return all(r.event_emitted for r in self.results)

    @property
    def failed_stages(self) -> list[str]:
        return [r.stage_name for r in self.results if not r.success]

    @property
    def stages_run(self) -> list[str]:
        return [r.stage_name for r in self.results]


def build_run_from_results(results: list[StageResult]) -> PipelineRun:
    run = PipelineRun()
    run.results = list(results)
    return run


def simulate_stage_result(
    stage: PipelineStage,
    duration_seconds: float,
    success: bool = True,
    event_emitted: bool = True,
    error_message: Optional[str] = None,
) -> StageResult:
    return StageResult(
        stage_name=stage.name,
        success=success,
        duration_seconds=duration_seconds,
        event_emitted=event_emitted if success else False,
        error_message=error_message if not success else None,
    )


def assert_no_dlq_loss(dlq_count: int) -> bool:
    if dlq_count < 0:
        raise ValueError("dlq_count must be >= 0")
    return dlq_count == DLQ_THRESHOLD


def pipeline_summary(run: PipelineRun) -> dict:
    return {
        "stages_run": len(run.results),
        "all_passed": run.all_passed,
        "total_duration_seconds": run.total_duration,
        "within_time_limit": run.within_time_limit,
        "all_events_emitted": run.all_events_emitted,
        "failed_stages": run.failed_stages,
    }
