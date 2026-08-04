"""Tests for event-to-memory-record generation — S13-02, S13-03, S13-04."""
import uuid

import pytest

from app.memory.event_handler import (
    _EVENT_CATEGORY,
    _EVENT_SUMMARIES,
    _SUBSCRIBED_EVENTS,
    extract_memory_record_from_event,
    extract_pattern_data_from_event,
)
from app.memory.schemas import MemoryRecordCreate


class TestSubscribedEvents:
    def test_is_frozenset(self):
        assert isinstance(_SUBSCRIBED_EVENTS, frozenset)

    def test_decision_approved_subscribed(self):
        assert "DecisionApproved" in _SUBSCRIBED_EVENTS

    def test_vendor_score_computed_subscribed(self):
        assert "VendorScoreComputed" in _SUBSCRIBED_EVENTS

    def test_risk_resolved_subscribed(self):
        assert "RiskResolved" in _SUBSCRIBED_EVENTS

    def test_risk_mitigated_subscribed(self):
        assert "RiskMitigated" in _SUBSCRIBED_EVENTS

    def test_has_four_events(self):
        assert len(_SUBSCRIBED_EVENTS) == 4


class TestEventCategory:
    def test_decision_approved_maps_to_decision(self):
        assert _EVENT_CATEGORY["DecisionApproved"] == "DECISION"

    def test_vendor_score_computed_maps_to_vendor(self):
        assert _EVENT_CATEGORY["VendorScoreComputed"] == "VENDOR"

    def test_risk_resolved_maps_to_risk(self):
        assert _EVENT_CATEGORY["RiskResolved"] == "RISK"

    def test_risk_mitigated_maps_to_risk(self):
        assert _EVENT_CATEGORY["RiskMitigated"] == "RISK"

    def test_all_subscribed_events_have_category(self):
        for event_type in _SUBSCRIBED_EVENTS:
            assert event_type in _EVENT_CATEGORY


class TestEventSummaries:
    def test_all_subscribed_events_have_summaries(self):
        for event_type in _SUBSCRIBED_EVENTS:
            assert event_type in _EVENT_SUMMARIES

    def test_summaries_are_non_empty(self):
        for event_type, summary in _EVENT_SUMMARIES.items():
            assert isinstance(summary, str)
            assert len(summary) > 0


class TestExtractMemoryRecordFromEvent:
    def _project_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def _event(self, event_type: str, **kwargs) -> dict:
        base = {"event_type": event_type, "event_id": "evt-001"}
        return {**base, **kwargs}

    def test_unknown_event_returns_none(self):
        result = extract_memory_record_from_event(
            {"event_type": "UnknownEvent"}, self._project_id()
        )
        assert result is None

    def test_empty_event_type_returns_none(self):
        result = extract_memory_record_from_event(
            {"event_type": ""}, self._project_id()
        )
        assert result is None

    def test_missing_event_type_returns_none(self):
        result = extract_memory_record_from_event({}, self._project_id())
        assert result is None

    def test_decision_approved_returns_record_create(self):
        result = extract_memory_record_from_event(
            self._event("DecisionApproved"), self._project_id()
        )
        assert isinstance(result, MemoryRecordCreate)

    def test_category_set_to_decision(self):
        result = extract_memory_record_from_event(
            self._event("DecisionApproved"), self._project_id()
        )
        assert result.category == "DECISION"

    def test_vendor_score_computed_category_vendor(self):
        result = extract_memory_record_from_event(
            self._event("VendorScoreComputed"), self._project_id()
        )
        assert result.category == "VENDOR"

    def test_risk_resolved_category_risk(self):
        result = extract_memory_record_from_event(
            self._event("RiskResolved"), self._project_id()
        )
        assert result.category == "RISK"

    def test_risk_mitigated_category_risk(self):
        result = extract_memory_record_from_event(
            self._event("RiskMitigated"), self._project_id()
        )
        assert result.category == "RISK"

    def test_project_id_set(self):
        pid = self._project_id()
        result = extract_memory_record_from_event(self._event("DecisionApproved"), pid)
        assert result.project_id == pid

    def test_summary_non_empty(self):
        result = extract_memory_record_from_event(
            self._event("VendorScoreComputed"), self._project_id()
        )
        assert len(result.summary) > 0

    def test_default_confidence_score(self):
        result = extract_memory_record_from_event(
            self._event("RiskResolved"), self._project_id()
        )
        assert 0.0 <= result.confidence_score <= 1.0

    def test_custom_confidence_score_clamped(self):
        result = extract_memory_record_from_event(
            self._event("DecisionApproved", confidence_score=2.5), self._project_id()
        )
        assert result.confidence_score <= 1.0

    def test_entity_id_extracted(self):
        eid = uuid.uuid4()
        result = extract_memory_record_from_event(
            self._event("DecisionApproved", entity_id=str(eid)), self._project_id()
        )
        assert result.entity_id == eid

    def test_invalid_entity_id_gives_none(self):
        result = extract_memory_record_from_event(
            self._event("DecisionApproved", entity_id="not-a-uuid"), self._project_id()
        )
        assert result.entity_id is None

    def test_entity_type_extracted(self):
        result = extract_memory_record_from_event(
            self._event("DecisionApproved", entity_type="vendor"), self._project_id()
        )
        assert result.entity_type == "vendor"

    def test_context_dict_extracted(self):
        result = extract_memory_record_from_event(
            self._event("VendorScoreComputed", context={"score": 75}), self._project_id()
        )
        assert result.context == {"score": 75}

    def test_non_dict_context_gives_none(self):
        result = extract_memory_record_from_event(
            self._event("DecisionApproved", context="not-a-dict"), self._project_id()
        )
        assert result.context is None

    def test_outcome_extracted(self):
        result = extract_memory_record_from_event(
            self._event("RiskResolved", outcome="Risk contained"), self._project_id()
        )
        assert result.outcome == "Risk contained"

    def test_all_subscribed_events_generate_record(self):
        pid = self._project_id()
        for event_type in _SUBSCRIBED_EVENTS:
            result = extract_memory_record_from_event({"event_type": event_type}, pid)
            assert isinstance(result, MemoryRecordCreate), f"Failed for {event_type}"


class TestExtractPatternDataFromEvent:
    def test_unknown_event_returns_none(self):
        assert extract_pattern_data_from_event({"event_type": "Unknown"}) is None

    def test_empty_event_type_returns_none(self):
        assert extract_pattern_data_from_event({"event_type": ""}) is None

    def test_known_event_returns_dict(self):
        result = extract_pattern_data_from_event({"event_type": "DecisionApproved"})
        assert isinstance(result, dict)

    def test_pattern_name_set(self):
        result = extract_pattern_data_from_event({"event_type": "DecisionApproved"})
        assert "pattern_name" in result
        assert len(result["pattern_name"]) > 0

    def test_category_set(self):
        result = extract_pattern_data_from_event({"event_type": "VendorScoreComputed"})
        assert result["category"] == "VENDOR"

    def test_trigger_conditions_from_context(self):
        result = extract_pattern_data_from_event({
            "event_type": "RiskResolved",
            "context": {"risk_type": "supply"},
        })
        assert result["trigger_conditions"].get("risk_type") == "supply"

    def test_outcome_extracted(self):
        result = extract_pattern_data_from_event({
            "event_type": "DecisionApproved",
            "outcome": "Approved with conditions",
        })
        assert result["outcome"] == "Approved with conditions"

    def test_confidence_score_clamped(self):
        result = extract_pattern_data_from_event({
            "event_type": "VendorScoreComputed",
            "confidence_score": 5.0,
        })
        assert result["confidence_score"] == 1.0

    def test_custom_pattern_name_from_context(self):
        result = extract_pattern_data_from_event({
            "event_type": "DecisionApproved",
            "context": {"pattern_name": "Custom pattern"},
        })
        assert result["pattern_name"] == "Custom pattern"
