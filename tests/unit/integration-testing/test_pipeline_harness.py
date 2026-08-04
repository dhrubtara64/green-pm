"""Tests for pipeline integration test harness — S18-03."""
import pytest

from app.pipeline.harness import (
    DLQ_THRESHOLD,
    PipelineRun,
    StageResult,
    assert_no_dlq_loss,
    build_run_from_results,
    pipeline_summary,
    simulate_stage_result,
)
from app.pipeline.stages import get_default_stages, stage_by_name


class TestDLQThreshold:
    def test_dlq_threshold_is_zero(self):
        assert DLQ_THRESHOLD == 0


class TestStageResult:
    def test_construction(self):
        r = StageResult("EVIDENCE_INGESTION", success=True, duration_seconds=2.5, event_emitted=True)
        assert r.stage_name == "EVIDENCE_INGESTION"

    def test_success_stored(self):
        r = StageResult("RISK_ASSESSMENT", success=False, duration_seconds=1.0, event_emitted=False)
        assert r.success is False

    def test_error_message_stored(self):
        r = StageResult("CLOSE_LOOP", success=False, duration_seconds=1.0, event_emitted=False, error_message="timeout")
        assert r.error_message == "timeout"


class TestPipelineRun:
    def test_empty_run_all_passed(self):
        run = PipelineRun()
        assert run.all_passed is True

    def test_all_passed_when_all_succeed(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=1.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert run.all_passed is True

    def test_not_all_passed_when_one_fails(self):
        results = [
            StageResult(s.name, success=(s.name != "RISK_ASSESSMENT"), duration_seconds=1.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert run.all_passed is False

    def test_total_duration_sum(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=3.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert run.total_duration == 3.0 * 7

    def test_within_time_limit_true(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=2.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert run.within_time_limit is True

    def test_within_time_limit_false_when_too_slow(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=10.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert run.within_time_limit is False

    def test_all_events_emitted(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=1.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert run.all_events_emitted is True

    def test_not_all_events_when_one_missing(self):
        stages = list(get_default_stages())
        results = [
            StageResult(s.name, success=True, duration_seconds=1.0, event_emitted=(i != 0))
            for i, s in enumerate(stages)
        ]
        run = build_run_from_results(results)
        assert run.all_events_emitted is False

    def test_failed_stages_list(self):
        results = [
            StageResult("EVIDENCE_INGESTION", success=False, duration_seconds=1.0, event_emitted=False),
            StageResult("EVIDENCE_SCORING", success=True, duration_seconds=1.0, event_emitted=True),
        ]
        run = build_run_from_results(results)
        assert run.failed_stages == ["EVIDENCE_INGESTION"]

    def test_stages_run_list(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=1.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        assert len(run.stages_run) == 7


class TestSimulateStageResult:
    def test_returns_stage_result(self):
        stage = stage_by_name("EVIDENCE_INGESTION")
        r = simulate_stage_result(stage, duration_seconds=2.0)
        assert isinstance(r, StageResult)

    def test_stage_name_set(self):
        stage = stage_by_name("RISK_ASSESSMENT")
        r = simulate_stage_result(stage, duration_seconds=1.0)
        assert r.stage_name == "RISK_ASSESSMENT"

    def test_success_default_true(self):
        stage = stage_by_name("EVIDENCE_INGESTION")
        r = simulate_stage_result(stage, duration_seconds=1.0)
        assert r.success is True

    def test_failure_clears_event(self):
        stage = stage_by_name("EVIDENCE_INGESTION")
        r = simulate_stage_result(stage, duration_seconds=1.0, success=False)
        assert r.event_emitted is False

    def test_error_message_on_failure(self):
        stage = stage_by_name("CLOSE_LOOP")
        r = simulate_stage_result(stage, duration_seconds=1.0, success=False, error_message="err")
        assert r.error_message == "err"

    def test_no_error_message_on_success(self):
        stage = stage_by_name("EVIDENCE_INGESTION")
        r = simulate_stage_result(stage, duration_seconds=1.0, success=True, error_message="oops")
        assert r.error_message is None


class TestAssertNoDLQLoss:
    def test_zero_passes(self):
        assert assert_no_dlq_loss(0) is True

    def test_one_fails(self):
        assert assert_no_dlq_loss(1) is False

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="dlq_count"):
            assert_no_dlq_loss(-1)


class TestPipelineSummary:
    def test_returns_dict(self):
        run = PipelineRun()
        assert isinstance(pipeline_summary(run), dict)

    def test_stages_run_count(self):
        results = [
            StageResult(s.name, success=True, duration_seconds=1.0, event_emitted=True)
            for s in get_default_stages()
        ]
        run = build_run_from_results(results)
        summary = pipeline_summary(run)
        assert summary["stages_run"] == 7

    def test_all_passed_key(self):
        run = PipelineRun()
        summary = pipeline_summary(run)
        assert "all_passed" in summary

    def test_within_time_limit_key(self):
        run = PipelineRun()
        summary = pipeline_summary(run)
        assert "within_time_limit" in summary
