"""Tests for pipeline stage definitions — S18-03."""
import pytest

from app.pipeline.stages import (
    MAX_PIPELINE_SECONDS,
    PIPELINE_STAGES,
    STAGE_COUNT,
    PipelineStage,
    get_default_stages,
    stage_by_name,
    stages_in_order,
    total_timeout,
    validate_pipeline,
)


class TestPipelineConstants:
    def test_seven_stages(self):
        assert STAGE_COUNT == 7

    def test_max_pipeline_seconds(self):
        assert MAX_PIPELINE_SECONDS == 30

    def test_evidence_ingestion_first(self):
        assert PIPELINE_STAGES[0] == "EVIDENCE_INGESTION"

    def test_close_loop_last(self):
        assert PIPELINE_STAGES[-1] == "CLOSE_LOOP"

    def test_all_expected_stages(self):
        expected = {
            "EVIDENCE_INGESTION", "EVIDENCE_SCORING", "IMPACT_ANALYSIS",
            "DEPENDENCY_CHECK", "RISK_ASSESSMENT", "COORDINATION_LOOP", "CLOSE_LOOP",
        }
        assert set(PIPELINE_STAGES) == expected


class TestPipelineStage:
    def test_valid_construction(self):
        s = PipelineStage("EVIDENCE_INGESTION", timeout_seconds=5, emits_event=True)
        assert s.name == "EVIDENCE_INGESTION"

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="Unknown stage"):
            PipelineStage("FAKE_STAGE", timeout_seconds=5, emits_event=True)

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            PipelineStage("EVIDENCE_INGESTION", timeout_seconds=0, emits_event=True)

    def test_is_frozen(self):
        s = PipelineStage("EVIDENCE_INGESTION", timeout_seconds=5, emits_event=True)
        with pytest.raises(Exception):
            s.name = "changed"

    def test_order_evidence_ingestion_zero(self):
        s = PipelineStage("EVIDENCE_INGESTION", timeout_seconds=5, emits_event=True)
        assert s.order == 0

    def test_order_close_loop_last(self):
        s = PipelineStage("CLOSE_LOOP", timeout_seconds=4, emits_event=True)
        assert s.order == 6

    def test_emits_event_stored(self):
        s = PipelineStage("RISK_ASSESSMENT", timeout_seconds=5, emits_event=False)
        assert s.emits_event is False


class TestGetDefaultStages:
    def test_returns_tuple(self):
        stages = get_default_stages()
        assert isinstance(stages, tuple)

    def test_seven_stages(self):
        stages = get_default_stages()
        assert len(stages) == STAGE_COUNT

    def test_all_stage_names_present(self):
        stages = get_default_stages()
        names = {s.name for s in stages}
        assert names == set(PIPELINE_STAGES)

    def test_all_emit_events(self):
        stages = get_default_stages()
        assert all(s.emits_event for s in stages)


class TestTotalTimeout:
    def test_sums_timeouts(self):
        stages = get_default_stages()
        expected = sum(s.timeout_seconds for s in stages)
        assert total_timeout(stages) == expected

    def test_single_stage(self):
        stage = PipelineStage("EVIDENCE_INGESTION", timeout_seconds=7, emits_event=True)
        assert total_timeout((stage,)) == 7

    def test_empty_is_zero(self):
        assert total_timeout(()) == 0


class TestStagesInOrder:
    def test_returns_list(self):
        stages = get_default_stages()
        result = stages_in_order(stages)
        assert isinstance(result, list)

    def test_correct_order(self):
        stages = get_default_stages()
        ordered = stages_in_order(stages)
        for i in range(len(ordered) - 1):
            assert ordered[i].order < ordered[i + 1].order


class TestValidatePipeline:
    def test_default_stages_valid(self):
        errors = validate_pipeline(get_default_stages())
        assert errors == []

    def test_over_timeout_fails(self):
        slow_stages = tuple(
            PipelineStage(name, timeout_seconds=10, emits_event=True)
            for name in PIPELINE_STAGES
        )
        errors = validate_pipeline(slow_stages)
        assert len(errors) > 0


class TestStageByName:
    def test_returns_stage(self):
        s = stage_by_name("EVIDENCE_INGESTION")
        assert isinstance(s, PipelineStage)

    def test_correct_name(self):
        s = stage_by_name("RISK_ASSESSMENT")
        assert s.name == "RISK_ASSESSMENT"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="UNKNOWN"):
            stage_by_name("UNKNOWN")

    def test_all_stages_findable(self):
        for name in PIPELINE_STAGES:
            s = stage_by_name(name)
            assert s.name == name
