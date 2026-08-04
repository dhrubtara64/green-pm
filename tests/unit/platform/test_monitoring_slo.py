"""Tests for SLO definitions and alert rules — S18-05."""
import pytest

from app.monitoring.slo import (
    DEFAULT_ERROR_RATE_THRESHOLD_PCT,
    DEFAULT_LATENCY_THRESHOLD_MS,
    ENGINE_COUNT,
    ENGINE_NAMES,
    SLO_WINDOW_DAYS,
    AlertRule,
    SLODefinition,
    build_all_alert_rules,
    build_error_rate_alert,
    build_latency_alert,
    slo_compliance,
)


class TestEngineRegistry:
    def test_engine_count_seventeen(self):
        assert ENGINE_COUNT == 17

    def test_engine_names_frozenset(self):
        assert isinstance(ENGINE_NAMES, frozenset)

    def test_evidence_engine_present(self):
        assert "evidence-engine" in ENGINE_NAMES

    def test_pig_service_present(self):
        assert "pig-service" in ENGINE_NAMES

    def test_recommendation_engine_present(self):
        assert "recommendation-engine" in ENGINE_NAMES

    def test_correct_count(self):
        assert len(ENGINE_NAMES) == ENGINE_COUNT

    def test_default_latency_threshold(self):
        assert DEFAULT_LATENCY_THRESHOLD_MS == 800

    def test_default_error_rate_threshold(self):
        assert DEFAULT_ERROR_RATE_THRESHOLD_PCT == 1.0

    def test_slo_window_days(self):
        assert SLO_WINDOW_DAYS == 30


class TestSLODefinition:
    def test_valid_construction(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        assert slo.engine_name == "evidence-engine"

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            SLODefinition("nonexistent-engine", latency_p99_ms=800, error_rate_max_pct=1.0)

    def test_zero_latency_raises(self):
        with pytest.raises(ValueError, match="latency_p99_ms"):
            SLODefinition("evidence-engine", latency_p99_ms=0, error_rate_max_pct=1.0)

    def test_zero_error_rate_raises(self):
        with pytest.raises(ValueError, match="error_rate_max_pct"):
            SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=0.0)

    def test_is_frozen(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        with pytest.raises(Exception):
            slo.engine_name = "changed"

    def test_availability_target(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        assert slo.availability_target_pct == 99.0

    def test_default_window_days(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        assert slo.window_days == SLO_WINDOW_DAYS

    def test_all_engines_valid(self):
        for engine in ENGINE_NAMES:
            slo = SLODefinition(engine, latency_p99_ms=800, error_rate_max_pct=1.0)
            assert slo.engine_name == engine


class TestAlertRule:
    def test_valid_construction(self):
        rule = AlertRule(
            engine_name="evidence-engine",
            metric="custom.googleapis.com/latency",
            threshold=800.0,
            comparison="GREATER_THAN",
            duration_seconds=300,
            severity="P1",
        )
        assert rule.engine_name == "evidence-engine"

    def test_invalid_comparison_raises(self):
        with pytest.raises(ValueError, match="comparison"):
            AlertRule("evidence-engine", "metric", 800.0, "INVALID", 300, "P1")

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="severity"):
            AlertRule("evidence-engine", "metric", 800.0, "GREATER_THAN", 300, "P5")

    def test_is_frozen(self):
        rule = AlertRule("evidence-engine", "metric", 800.0, "GREATER_THAN", 300, "P1")
        with pytest.raises(Exception):
            rule.threshold = 999.0


class TestBuildLatencyAlert:
    def test_returns_alert_rule(self):
        rule = build_latency_alert("evidence-engine")
        assert isinstance(rule, AlertRule)

    def test_engine_name_set(self):
        rule = build_latency_alert("pig-service")
        assert rule.engine_name == "pig-service"

    def test_default_threshold_800ms(self):
        rule = build_latency_alert("evidence-engine")
        assert rule.threshold == 800.0

    def test_custom_threshold(self):
        rule = build_latency_alert("evidence-engine", threshold_ms=500)
        assert rule.threshold == 500.0

    def test_comparison_greater_than(self):
        rule = build_latency_alert("evidence-engine")
        assert rule.comparison == "GREATER_THAN"

    def test_severity_p1(self):
        rule = build_latency_alert("evidence-engine")
        assert rule.severity == "P1"

    def test_metric_contains_engine_name(self):
        rule = build_latency_alert("evidence-engine")
        assert "evidence-engine" in rule.metric

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            build_latency_alert("fake-engine")


class TestBuildErrorRateAlert:
    def test_returns_alert_rule(self):
        rule = build_error_rate_alert("evidence-engine")
        assert isinstance(rule, AlertRule)

    def test_default_threshold(self):
        rule = build_error_rate_alert("evidence-engine")
        assert rule.threshold == DEFAULT_ERROR_RATE_THRESHOLD_PCT

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            build_error_rate_alert("fake-engine")


class TestSLOCompliance:
    def test_compliant_when_both_ok(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        result = slo_compliance(slo, observed_p99_ms=600.0, observed_error_rate_pct=0.5)
        assert result["compliant"] is True

    def test_non_compliant_on_latency(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        result = slo_compliance(slo, observed_p99_ms=900.0, observed_error_rate_pct=0.5)
        assert result["compliant"] is False

    def test_non_compliant_on_error_rate(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        result = slo_compliance(slo, observed_p99_ms=600.0, observed_error_rate_pct=2.0)
        assert result["compliant"] is False

    def test_engine_in_result(self):
        slo = SLODefinition("evidence-engine", latency_p99_ms=800, error_rate_max_pct=1.0)
        result = slo_compliance(slo, 600.0, 0.5)
        assert result["engine"] == "evidence-engine"


class TestBuildAllAlertRules:
    def test_returns_list(self):
        rules = build_all_alert_rules()
        assert isinstance(rules, list)

    def test_two_rules_per_engine(self):
        rules = build_all_alert_rules()
        assert len(rules) == ENGINE_COUNT * 2

    def test_all_engines_covered(self):
        rules = build_all_alert_rules()
        engine_names = {r.engine_name for r in rules}
        assert engine_names == ENGINE_NAMES
