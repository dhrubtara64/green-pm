"""Tests for load test SLO assertions — S18-02."""
import pytest

from app.load.assertions import (
    EVIDENCE_SCORE_P99_MS,
    MAX_ERROR_RATE_PCT,
    PIG_QUERY_P99_MS,
    SLOResult,
    assert_error_rate,
    assert_evidence_score_slo,
    assert_pig_query_slo,
    assert_slo,
    summarise_suite_results,
)
from app.load.scenarios import build_scenario


class TestSLOConstants:
    def test_pig_query_p99_800ms(self):
        assert PIG_QUERY_P99_MS == 800

    def test_evidence_score_p99_200ms(self):
        assert EVIDENCE_SCORE_P99_MS == 200

    def test_max_error_rate_01pct(self):
        assert MAX_ERROR_RATE_PCT == 0.1


class TestSLOResult:
    def test_latency_passed_when_below_threshold(self):
        r = SLOResult("PIG_QUERY", p99_ms=500.0, error_rate_pct=0.0, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.latency_passed is True

    def test_latency_failed_when_above_threshold(self):
        r = SLOResult("PIG_QUERY", p99_ms=900.0, error_rate_pct=0.0, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.latency_passed is False

    def test_error_rate_passed_when_below_max(self):
        r = SLOResult("PIG_QUERY", p99_ms=500.0, error_rate_pct=0.05, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.error_rate_passed is True

    def test_error_rate_failed_when_above_max(self):
        r = SLOResult("PIG_QUERY", p99_ms=500.0, error_rate_pct=0.5, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.error_rate_passed is False

    def test_passed_when_both_ok(self):
        r = SLOResult("PIG_QUERY", p99_ms=500.0, error_rate_pct=0.05, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.passed is True

    def test_failed_when_latency_bad(self):
        r = SLOResult("PIG_QUERY", p99_ms=900.0, error_rate_pct=0.0, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.passed is False

    def test_failure_reasons_on_latency_breach(self):
        r = SLOResult("PIG_QUERY", p99_ms=900.0, error_rate_pct=0.0, threshold_ms=800, max_error_rate_pct=0.1)
        assert len(r.failure_reasons) == 1
        assert "P99" in r.failure_reasons[0]

    def test_failure_reasons_empty_on_pass(self):
        r = SLOResult("PIG_QUERY", p99_ms=500.0, error_rate_pct=0.0, threshold_ms=800, max_error_rate_pct=0.1)
        assert r.failure_reasons == []


class TestAssertSLO:
    def test_returns_slo_result(self):
        scenario = build_scenario("PIG_QUERY")
        result = assert_slo(scenario, p99_ms=600.0, error_rate_pct=0.05)
        assert isinstance(result, SLOResult)

    def test_scenario_name_set(self):
        scenario = build_scenario("PIG_QUERY")
        result = assert_slo(scenario, p99_ms=600.0, error_rate_pct=0.05)
        assert result.scenario_name == "PIG_QUERY"

    def test_passed_on_good_values(self):
        scenario = build_scenario("PIG_QUERY")
        result = assert_slo(scenario, p99_ms=600.0, error_rate_pct=0.05)
        assert result.passed is True

    def test_failed_on_bad_latency(self):
        scenario = build_scenario("EVIDENCE_SCORE")
        result = assert_slo(scenario, p99_ms=500.0, error_rate_pct=0.0)
        assert result.passed is False


class TestAssertPigQuerySlo:
    def test_passes_below_800ms(self):
        assert assert_pig_query_slo(799) is True

    def test_passes_at_800ms(self):
        assert assert_pig_query_slo(800) is True

    def test_fails_above_800ms(self):
        assert assert_pig_query_slo(801) is False

    def test_passes_at_zero(self):
        assert assert_pig_query_slo(0) is True


class TestAssertEvidenceScoreSlo:
    def test_passes_below_200ms(self):
        assert assert_evidence_score_slo(199) is True

    def test_passes_at_200ms(self):
        assert assert_evidence_score_slo(200) is True

    def test_fails_above_200ms(self):
        assert assert_evidence_score_slo(201) is False


class TestAssertErrorRate:
    def test_passes_at_zero(self):
        assert assert_error_rate(0.0) is True

    def test_passes_at_threshold(self):
        assert assert_error_rate(0.1) is True

    def test_fails_above_threshold(self):
        assert assert_error_rate(0.11) is False

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="error_rate_pct"):
            assert_error_rate(-0.1)


class TestSummariseSuiteResults:
    def test_all_passed(self):
        r1 = SLOResult("PIG_QUERY", 500, 0.0, 800, 0.1)
        r2 = SLOResult("EVIDENCE_SCORE", 100, 0.0, 200, 0.1)
        summary = summarise_suite_results([r1, r2])
        assert summary["all_passed"] is True

    def test_total_count(self):
        results = [SLOResult("PIG_QUERY", 500, 0.0, 800, 0.1)] * 3
        summary = summarise_suite_results(results)
        assert summary["total"] == 3

    def test_failed_count_when_one_fails(self):
        r1 = SLOResult("PIG_QUERY", 900, 0.0, 800, 0.1)
        r2 = SLOResult("EVIDENCE_SCORE", 100, 0.0, 200, 0.1)
        summary = summarise_suite_results([r1, r2])
        assert summary["failed"] == 1

    def test_failures_list_populated(self):
        r1 = SLOResult("PIG_QUERY", 900, 0.0, 800, 0.1)
        summary = summarise_suite_results([r1])
        assert len(summary["failures"]) == 1

    def test_empty_list(self):
        summary = summarise_suite_results([])
        assert summary["total"] == 0
        assert summary["all_passed"] is True
