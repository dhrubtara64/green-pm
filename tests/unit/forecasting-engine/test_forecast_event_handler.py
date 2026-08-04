"""Tests for Forecasting Engine event handler — S14-02."""
import pytest

from app.forecast.event_handler import (
    _EVENT_DOMAINS,
    _SUBSCRIBED_EVENTS,
    extract_domain_forecast,
    get_affected_domains,
)
from app.forecast.schemas import _FORECAST_DOMAINS


class TestSubscribedEvents:
    def test_is_frozenset(self):
        assert isinstance(_SUBSCRIBED_EVENTS, frozenset)

    def test_has_seventeen_events(self):
        assert len(_SUBSCRIBED_EVENTS) == 17

    def test_critical_path_changed_subscribed(self):
        assert "CriticalPathChanged" in _SUBSCRIBED_EVENTS

    def test_simulation_completed_subscribed(self):
        assert "SimulationCompleted" in _SUBSCRIBED_EVENTS

    def test_risk_identified_subscribed(self):
        assert "RiskIdentified" in _SUBSCRIBED_EVENTS

    def test_vendor_delay_flagged_subscribed(self):
        assert "VendorDelayFlagged" in _SUBSCRIBED_EVENTS

    def test_readiness_gate_blocked_subscribed(self):
        assert "ReadinessGateBlocked" in _SUBSCRIBED_EVENTS

    def test_evidence_reviewed_subscribed(self):
        assert "EvidenceReviewed" in _SUBSCRIBED_EVENTS

    def test_impact_assessed_subscribed(self):
        assert "ImpactAssessed" in _SUBSCRIBED_EVENTS

    def test_decision_approved_subscribed(self):
        assert "DecisionApproved" in _SUBSCRIBED_EVENTS


class TestEventDomains:
    def test_all_subscribed_events_have_domains(self):
        for event_type in _SUBSCRIBED_EVENTS:
            assert event_type in _EVENT_DOMAINS, f"Missing: {event_type}"

    def test_all_domain_values_are_frozensets(self):
        for event_type, domains in _EVENT_DOMAINS.items():
            assert isinstance(domains, frozenset), f"Not frozenset for {event_type}"

    def test_all_domains_are_valid(self):
        for event_type, domains in _EVENT_DOMAINS.items():
            for d in domains:
                assert d in _FORECAST_DOMAINS, f"Invalid domain {d} for {event_type}"

    def test_critical_path_changed_affects_schedule(self):
        assert "SCHEDULE" in _EVENT_DOMAINS["CriticalPathChanged"]

    def test_risk_identified_affects_budget(self):
        assert "BUDGET" in _EVENT_DOMAINS["RiskIdentified"]

    def test_vendor_delay_affects_cash_flow(self):
        assert "CASH_FLOW" in _EVENT_DOMAINS["VendorDelayFlagged"]

    def test_evidence_reviewed_affects_quality(self):
        assert "QUALITY" in _EVENT_DOMAINS["EvidenceReviewed"]

    def test_readiness_gate_cleared_affects_commissioning(self):
        assert "COMMISSIONING" in _EVENT_DOMAINS["ReadinessGateCleared"]


class TestGetAffectedDomains:
    def test_known_event_returns_frozenset(self):
        result = get_affected_domains("RiskIdentified")
        assert isinstance(result, frozenset)

    def test_known_event_returns_non_empty(self):
        result = get_affected_domains("SimulationCompleted")
        assert len(result) > 0

    def test_unknown_event_returns_empty_frozenset(self):
        result = get_affected_domains("UnknownEvent")
        assert result == frozenset()

    def test_empty_string_returns_empty(self):
        assert get_affected_domains("") == frozenset()


class TestExtractDomainForecast:
    def _event(self, event_type: str, **kw) -> dict:
        return {"event_type": event_type, **kw}

    def test_unknown_event_returns_none(self):
        assert extract_domain_forecast({"event_type": "Unknown"}, "SCHEDULE") is None

    def test_empty_event_type_returns_none(self):
        assert extract_domain_forecast({"event_type": ""}, "BUDGET") is None

    def test_missing_event_type_returns_none(self):
        assert extract_domain_forecast({}, "QUALITY") is None

    def test_domain_not_affected_returns_none(self):
        # EvidenceReviewed only affects QUALITY
        result = extract_domain_forecast(self._event("EvidenceReviewed"), "SCHEDULE")
        assert result is None

    def test_affected_domain_returns_dict(self):
        result = extract_domain_forecast(self._event("RiskIdentified"), "SCHEDULE")
        assert isinstance(result, dict)

    def test_result_has_required_keys(self):
        result = extract_domain_forecast(self._event("CriticalPathChanged"), "SCHEDULE")
        assert {"current_value", "forecast_value", "confidence", "trend"} <= result.keys()

    def test_default_confidence_is_07(self):
        result = extract_domain_forecast(self._event("RiskIdentified"), "BUDGET")
        assert result["confidence"] == pytest.approx(0.7)

    def test_custom_confidence_extracted(self):
        result = extract_domain_forecast(
            self._event("SimulationCompleted", confidence_score=0.9), "SCHEDULE"
        )
        assert result["confidence"] == pytest.approx(0.9)

    def test_confidence_clamped_above_one(self):
        result = extract_domain_forecast(
            self._event("VendorDelayFlagged", confidence_score=2.5), "SCHEDULE"
        )
        assert result["confidence"] == pytest.approx(1.0)

    def test_confidence_clamped_below_zero(self):
        result = extract_domain_forecast(
            self._event("VendorDelayFlagged", confidence_score=-1.0), "BUDGET"
        )
        assert result["confidence"] == pytest.approx(0.0)

    def test_risk_identified_schedule_trend_down(self):
        result = extract_domain_forecast(self._event("RiskIdentified"), "SCHEDULE")
        assert result["trend"] == "DOWN"

    def test_risk_resolved_schedule_trend_up(self):
        result = extract_domain_forecast(self._event("RiskResolved"), "SCHEDULE")
        assert result["trend"] == "UP"

    def test_readiness_gate_cleared_commissioning_trend_up(self):
        result = extract_domain_forecast(self._event("ReadinessGateCleared"), "COMMISSIONING")
        assert result["trend"] == "UP"

    def test_supply_chain_disrupted_budget_trend_down(self):
        result = extract_domain_forecast(self._event("SupplyChainDisrupted"), "BUDGET")
        assert result["trend"] == "DOWN"

    def test_default_current_value_zero(self):
        result = extract_domain_forecast(self._event("ImpactAssessed"), "SCHEDULE")
        assert result["current_value"] == pytest.approx(0.0)

    def test_custom_current_value_extracted(self):
        result = extract_domain_forecast(
            self._event("SimulationCompleted", current_value=120.5), "BUDGET"
        )
        assert result["current_value"] == pytest.approx(120.5)

    def test_forecast_value_defaults_to_current_value(self):
        result = extract_domain_forecast(
            self._event("CriticalPathChanged", current_value=50.0), "SCHEDULE"
        )
        assert result["forecast_value"] == pytest.approx(50.0)
