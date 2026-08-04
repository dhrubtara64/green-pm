"""Tests for event-to-coordination-item generation — S12-02."""
import uuid

import pytest

from app.coordination.event_handler import (
    _EVENT_TITLES,
    _SUBSCRIBED_EVENTS,
    generate_coordination_items,
    is_duplicate_event,
)
from app.coordination.schemas import CoordinationItemCreate


class TestSubscribedEvents:
    def test_is_frozenset(self):
        assert isinstance(_SUBSCRIBED_EVENTS, frozenset)

    def test_has_eight_events(self):
        assert len(_SUBSCRIBED_EVENTS) == 8

    def test_risk_identified_subscribed(self):
        assert "RiskIdentified" in _SUBSCRIBED_EVENTS

    def test_risk_escalated_subscribed(self):
        assert "RiskEscalated" in _SUBSCRIBED_EVENTS

    def test_readiness_gate_updated_subscribed(self):
        assert "ReadinessGateUpdated" in _SUBSCRIBED_EVENTS

    def test_supply_chain_delay_subscribed(self):
        assert "SupplyChainDelayDetected" in _SUBSCRIBED_EVENTS

    def test_vendor_performance_subscribed(self):
        assert "VendorPerformanceFlagged" in _SUBSCRIBED_EVENTS

    def test_impact_assessment_subscribed(self):
        assert "ImpactAssessmentCompleted" in _SUBSCRIBED_EVENTS

    def test_critical_path_changed_subscribed(self):
        assert "CriticalPathChanged" in _SUBSCRIBED_EVENTS

    def test_simulation_projection_subscribed(self):
        assert "SimulationProjectionCompleted" in _SUBSCRIBED_EVENTS


class TestEventTitles:
    def test_all_subscribed_events_have_titles(self):
        for event_type in _SUBSCRIBED_EVENTS:
            assert event_type in _EVENT_TITLES, f"Missing title for {event_type}"

    def test_titles_are_non_empty_strings(self):
        for event_type, title in _EVENT_TITLES.items():
            assert isinstance(title, str)
            assert len(title) > 0


class TestGenerateCoordinationItems:
    def _project_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def _event(self, event_type: str, event_id: str = "evt-001") -> dict:
        return {"event_type": event_type, "event_id": event_id}

    def test_unknown_event_returns_empty_list(self):
        result = generate_coordination_items(
            {"event_type": "UnknownEvent", "event_id": "X"}, self._project_id()
        )
        assert result == []

    def test_empty_event_type_returns_empty_list(self):
        result = generate_coordination_items(
            {"event_type": "", "event_id": "X"}, self._project_id()
        )
        assert result == []

    def test_missing_event_type_returns_empty_list(self):
        result = generate_coordination_items({}, self._project_id())
        assert result == []

    def test_subscribed_event_returns_one_item(self):
        result = generate_coordination_items(
            self._event("RiskIdentified"), self._project_id()
        )
        assert len(result) == 1

    def test_returns_coordination_item_create(self):
        result = generate_coordination_items(
            self._event("RiskIdentified"), self._project_id()
        )
        assert isinstance(result[0], CoordinationItemCreate)

    def test_source_event_id_set(self):
        result = generate_coordination_items(
            self._event("RiskIdentified", "evt-xyz"), self._project_id()
        )
        assert result[0].source_event_id == "evt-xyz"

    def test_project_id_set(self):
        pid = uuid.uuid4()
        result = generate_coordination_items(self._event("RiskEscalated"), pid)
        assert result[0].project_id == pid

    def test_title_non_empty(self):
        result = generate_coordination_items(
            self._event("ReadinessGateUpdated"), self._project_id()
        )
        assert len(result[0].title) > 0

    def test_all_subscribed_events_generate_items(self):
        pid = self._project_id()
        for i, event_type in enumerate(_SUBSCRIBED_EVENTS):
            result = generate_coordination_items(
                {"event_type": event_type, "event_id": f"evt-{i}"}, pid
            )
            assert len(result) == 1, f"Expected 1 item for {event_type}"

    def test_risk_identified_has_specific_title(self):
        result = generate_coordination_items(
            self._event("RiskIdentified"), self._project_id()
        )
        assert "risk" in result[0].title.lower()

    def test_critical_path_changed_has_specific_title(self):
        result = generate_coordination_items(
            self._event("CriticalPathChanged"), self._project_id()
        )
        assert "critical" in result[0].title.lower() or "path" in result[0].title.lower()


class TestIsDuplicateEvent:
    def test_empty_set_not_duplicate(self):
        assert not is_duplicate_event(set(), "evt-001")

    def test_known_event_is_duplicate(self):
        assert is_duplicate_event({"evt-001", "evt-002"}, "evt-001")

    def test_unknown_event_not_duplicate(self):
        assert not is_duplicate_event({"evt-001"}, "evt-999")

    def test_empty_source_event_id_not_duplicate(self):
        assert not is_duplicate_event({"evt-001"}, "")

    def test_exact_match_required(self):
        assert not is_duplicate_event({"evt-001-x"}, "evt-001")
