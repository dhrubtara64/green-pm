"""Tests for runbook schema and builder — S18-05."""
import pytest

from app.monitoring.runbook import (
    RUNBOOK_SECTIONS,
    SECTION_COUNT,
    RunbookSpec,
    build_all_runbooks,
    build_runbook,
    runbook_index,
    validate_runbook_coverage,
)
from app.monitoring.slo import ENGINE_COUNT, ENGINE_NAMES


class TestRunbookConstants:
    def test_six_sections(self):
        assert SECTION_COUNT == 6

    def test_overview_present(self):
        assert "OVERVIEW" in RUNBOOK_SECTIONS

    def test_alert_playbook_present(self):
        assert "ALERT_PLAYBOOK" in RUNBOOK_SECTIONS

    def test_rollback_steps_present(self):
        assert "ROLLBACK_STEPS" in RUNBOOK_SECTIONS

    def test_escalation_path_present(self):
        assert "ESCALATION_PATH" in RUNBOOK_SECTIONS

    def test_slo_thresholds_present(self):
        assert "SLO_THRESHOLDS" in RUNBOOK_SECTIONS

    def test_architecture_present(self):
        assert "ARCHITECTURE" in RUNBOOK_SECTIONS


class TestRunbookSpec:
    def test_valid_construction(self):
        rb = RunbookSpec(
            engine_name="evidence-engine",
            title="Evidence Engine Runbook",
            version="1.0.0",
            sections=frozenset(RUNBOOK_SECTIONS),
            on_call_team="platform-oncall",
        )
        assert rb.engine_name == "evidence-engine"

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            RunbookSpec("fake-engine", "Title", "1.0", frozenset(RUNBOOK_SECTIONS), "team")

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            RunbookSpec("evidence-engine", "", "1.0", frozenset(RUNBOOK_SECTIONS), "team")

    def test_unknown_section_raises(self):
        with pytest.raises(ValueError, match="Unknown sections"):
            RunbookSpec("evidence-engine", "Title", "1.0", frozenset({"FAKE_SECTION"}), "team")

    def test_empty_on_call_team_raises(self):
        with pytest.raises(ValueError, match="on_call_team"):
            RunbookSpec("evidence-engine", "Title", "1.0", frozenset(RUNBOOK_SECTIONS), "")

    def test_is_frozen(self):
        rb = RunbookSpec("evidence-engine", "Title", "1.0", frozenset(RUNBOOK_SECTIONS), "team")
        with pytest.raises(Exception):
            rb.version = "2.0"

    def test_is_complete_when_all_sections(self):
        rb = RunbookSpec(
            "evidence-engine", "Title", "1.0", frozenset(RUNBOOK_SECTIONS), "team"
        )
        assert rb.is_complete is True

    def test_not_complete_when_missing_sections(self):
        rb = RunbookSpec(
            "evidence-engine", "Title", "1.0", frozenset({"OVERVIEW"}), "team"
        )
        assert rb.is_complete is False


class TestBuildRunbook:
    def test_returns_runbook_spec(self):
        rb = build_runbook("evidence-engine")
        assert isinstance(rb, RunbookSpec)

    def test_engine_name_set(self):
        rb = build_runbook("pig-service")
        assert rb.engine_name == "pig-service"

    def test_all_sections_included(self):
        rb = build_runbook("evidence-engine")
        assert rb.sections == frozenset(RUNBOOK_SECTIONS)

    def test_is_complete(self):
        rb = build_runbook("evidence-engine")
        assert rb.is_complete is True

    def test_default_version(self):
        rb = build_runbook("evidence-engine")
        assert rb.version == "1.0.0"

    def test_custom_version(self):
        rb = build_runbook("evidence-engine", version="2.0.0")
        assert rb.version == "2.0.0"

    def test_title_contains_engine(self):
        rb = build_runbook("risk-engine")
        assert "risk" in rb.title.lower()

    def test_default_on_call_team(self):
        rb = build_runbook("evidence-engine")
        assert rb.on_call_team == "platform-oncall"

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            build_runbook("fake-engine")

    def test_all_engines_buildable(self):
        for engine in ENGINE_NAMES:
            rb = build_runbook(engine)
            assert rb.engine_name == engine


class TestBuildAllRunbooks:
    def test_returns_list(self):
        runbooks = build_all_runbooks()
        assert isinstance(runbooks, list)

    def test_count_matches_engine_count(self):
        runbooks = build_all_runbooks()
        assert len(runbooks) == ENGINE_COUNT

    def test_all_engines_covered(self):
        runbooks = build_all_runbooks()
        names = {rb.engine_name for rb in runbooks}
        assert names == ENGINE_NAMES

    def test_all_complete(self):
        runbooks = build_all_runbooks()
        assert all(rb.is_complete for rb in runbooks)


class TestRunbookIndex:
    def test_returns_dict(self):
        runbooks = build_all_runbooks()
        index = runbook_index(runbooks)
        assert isinstance(index, dict)

    def test_all_engines_in_index(self):
        runbooks = build_all_runbooks()
        index = runbook_index(runbooks)
        assert set(index.keys()) == ENGINE_NAMES

    def test_titles_are_strings(self):
        runbooks = build_all_runbooks()
        index = runbook_index(runbooks)
        assert all(isinstance(v, str) for v in index.values())


class TestValidateRunbookCoverage:
    def test_no_missing_when_all_covered(self):
        runbooks = build_all_runbooks()
        missing = validate_runbook_coverage(runbooks)
        assert missing == []

    def test_missing_when_one_excluded(self):
        runbooks = build_all_runbooks()
        partial = [rb for rb in runbooks if rb.engine_name != "pig-service"]
        missing = validate_runbook_coverage(partial)
        assert "pig-service" in missing

    def test_returns_sorted_list(self):
        partial = build_all_runbooks()[:5]
        missing = validate_runbook_coverage(partial)
        assert missing == sorted(missing)

    def test_empty_list_returns_all_missing(self):
        missing = validate_runbook_coverage([])
        assert set(missing) == ENGINE_NAMES
