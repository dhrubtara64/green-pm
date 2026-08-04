"""Tests for load test scenario definitions — S18-02."""
import pytest

from app.load.scenarios import (
    CONCURRENT_USERS_TARGET,
    MAX_ERROR_RATE_PCT,
    SCENARIO_NAMES,
    SUSTAIN_MINUTES,
    LoadScenario,
    build_scenario,
    build_standard_suite,
    scenario_summary,
)


class TestScenarioConstants:
    def test_concurrent_users_target(self):
        assert CONCURRENT_USERS_TARGET == 150

    def test_sustain_minutes(self):
        assert SUSTAIN_MINUTES == 30

    def test_max_error_rate_pct(self):
        assert MAX_ERROR_RATE_PCT == 0.1

    def test_five_scenario_names(self):
        assert len(SCENARIO_NAMES) == 5

    def test_pig_query_present(self):
        assert "PIG_QUERY" in SCENARIO_NAMES

    def test_evidence_score_present(self):
        assert "EVIDENCE_SCORE" in SCENARIO_NAMES

    def test_full_pipeline_present(self):
        assert "FULL_PIPELINE" in SCENARIO_NAMES

    def test_scenario_names_is_frozenset(self):
        assert isinstance(SCENARIO_NAMES, frozenset)


class TestLoadScenario:
    def test_valid_construction(self):
        s = LoadScenario(
            name="PIG_QUERY",
            concurrent_users=150,
            sustain_minutes=30,
            p99_threshold_ms=800,
        )
        assert s.name == "PIG_QUERY"

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            LoadScenario(
                name="UNKNOWN_SCENARIO",
                concurrent_users=10,
                sustain_minutes=5,
                p99_threshold_ms=100,
            )

    def test_zero_users_raises(self):
        with pytest.raises(ValueError, match="concurrent_users"):
            LoadScenario("PIG_QUERY", 0, 30, 800)

    def test_zero_sustain_raises(self):
        with pytest.raises(ValueError, match="sustain_minutes"):
            LoadScenario("PIG_QUERY", 10, 0, 800)

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="p99_threshold_ms"):
            LoadScenario("PIG_QUERY", 10, 5, 0)

    def test_zero_error_rate_raises(self):
        with pytest.raises(ValueError, match="error_rate_max_pct"):
            LoadScenario("PIG_QUERY", 10, 5, 100, error_rate_max_pct=0.0)

    def test_is_frozen(self):
        s = LoadScenario("PIG_QUERY", 10, 5, 100)
        with pytest.raises(Exception):
            s.name = "changed"

    def test_total_duration_calculation(self):
        s = LoadScenario("PIG_QUERY", 150, 30, 800, ramp_up_seconds=60)
        assert s.total_duration_seconds == 60 + 30 * 60

    def test_default_ramp_up_is_sixty(self):
        s = LoadScenario("PIG_QUERY", 10, 5, 100)
        assert s.ramp_up_seconds == 60

    def test_default_error_rate(self):
        s = LoadScenario("PIG_QUERY", 10, 5, 100)
        assert s.error_rate_max_pct == MAX_ERROR_RATE_PCT


class TestBuildScenario:
    def test_returns_load_scenario(self):
        s = build_scenario("PIG_QUERY")
        assert isinstance(s, LoadScenario)

    def test_pig_query_threshold_800ms(self):
        s = build_scenario("PIG_QUERY")
        assert s.p99_threshold_ms == 800

    def test_evidence_score_threshold_200ms(self):
        s = build_scenario("EVIDENCE_SCORE")
        assert s.p99_threshold_ms == 200

    def test_default_users_150(self):
        s = build_scenario("PIG_QUERY")
        assert s.concurrent_users == CONCURRENT_USERS_TARGET

    def test_default_sustain_30_minutes(self):
        s = build_scenario("PIG_QUERY")
        assert s.sustain_minutes == SUSTAIN_MINUTES

    def test_custom_user_count(self):
        s = build_scenario("PIG_QUERY", concurrent_users=50)
        assert s.concurrent_users == 50

    def test_unknown_name_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            build_scenario("NO_SUCH_SCENARIO")

    def test_all_scenarios_buildable(self):
        for name in SCENARIO_NAMES:
            s = build_scenario(name)
            assert s.name == name


class TestBuildStandardSuite:
    def test_returns_list(self):
        suite = build_standard_suite()
        assert isinstance(suite, list)

    def test_all_scenarios_included(self):
        suite = build_standard_suite()
        names = {s.name for s in suite}
        assert names == SCENARIO_NAMES

    def test_no_duplicates(self):
        suite = build_standard_suite()
        names = [s.name for s in suite]
        assert len(names) == len(set(names))


class TestScenarioSummary:
    def test_returns_dict(self):
        s = build_scenario("PIG_QUERY")
        summary = scenario_summary(s)
        assert isinstance(summary, dict)

    def test_name_in_summary(self):
        s = build_scenario("PIG_QUERY")
        summary = scenario_summary(s)
        assert summary["name"] == "PIG_QUERY"

    def test_users_in_summary(self):
        s = build_scenario("PIG_QUERY")
        summary = scenario_summary(s)
        assert summary["users"] == 150

    def test_threshold_in_summary(self):
        s = build_scenario("PIG_QUERY")
        summary = scenario_summary(s)
        assert summary["p99_threshold_ms"] == 800

    def test_total_seconds_in_summary(self):
        s = build_scenario("PIG_QUERY")
        summary = scenario_summary(s)
        assert summary["total_seconds"] == s.total_duration_seconds
