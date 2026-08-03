"""Tests for Risk Engine domain and API schemas — S9-01, S9-04, S9-05, S9-06."""
import uuid
from datetime import date, datetime

import pytest
from dataclasses import FrozenInstanceError
from pydantic import ValidationError

from app.risk.schemas import (
    HeatMapCoordinates,
    MitigationEffectivenessUpdate,
    MitigationStatus,
    RiskAssessmentCreate,
    RiskAssessmentResponse,
    RiskCreate,
    RiskMitigationCreate,
    RiskMitigationResponse,
    RiskPatternMatch,
    RiskRegisterEntry,
    RiskResponse,
    RiskStatus,
    _MITIGATION_STATUSES,
    _RISK_STATUSES,
)


class TestRiskStatusEnum:
    def test_open_value(self):
        assert RiskStatus.OPEN == "OPEN"

    def test_mitigating_value(self):
        assert RiskStatus.MITIGATING == "MITIGATING"

    def test_closed_value(self):
        assert RiskStatus.CLOSED == "CLOSED"

    def test_three_statuses(self):
        assert len(RiskStatus) == 3

    def test_risk_statuses_frozenset(self):
        assert "OPEN" in _RISK_STATUSES
        assert "MITIGATING" in _RISK_STATUSES
        assert "CLOSED" in _RISK_STATUSES


class TestMitigationStatusEnum:
    def test_open_value(self):
        assert MitigationStatus.OPEN == "OPEN"

    def test_in_progress_value(self):
        assert MitigationStatus.IN_PROGRESS == "IN_PROGRESS"

    def test_closed_value(self):
        assert MitigationStatus.CLOSED == "CLOSED"

    def test_three_statuses(self):
        assert len(MitigationStatus) == 3

    def test_mitigation_statuses_frozenset(self):
        assert "OPEN" in _MITIGATION_STATUSES
        assert "IN_PROGRESS" in _MITIGATION_STATUSES
        assert "CLOSED" in _MITIGATION_STATUSES


class TestHeatMapCoordinates:
    def test_stores_x(self):
        h = HeatMapCoordinates(x=0.4, y=0.6)
        assert h.x == 0.4

    def test_stores_y(self):
        h = HeatMapCoordinates(x=0.4, y=0.6)
        assert h.y == 0.6

    def test_is_frozen(self):
        h = HeatMapCoordinates(x=0.4, y=0.6)
        with pytest.raises(FrozenInstanceError):
            h.x = 0.9  # type: ignore[misc]

    def test_zero_coordinates_valid(self):
        h = HeatMapCoordinates(x=0.0, y=0.0)
        assert h.x == 0.0 and h.y == 0.0

    def test_one_coordinates_valid(self):
        h = HeatMapCoordinates(x=1.0, y=1.0)
        assert h.x == 1.0 and h.y == 1.0

    def test_x_below_zero_raises(self):
        with pytest.raises(ValueError, match="x"):
            HeatMapCoordinates(x=-0.1, y=0.5)

    def test_x_above_one_raises(self):
        with pytest.raises(ValueError, match="x"):
            HeatMapCoordinates(x=1.1, y=0.5)

    def test_y_below_zero_raises(self):
        with pytest.raises(ValueError, match="y"):
            HeatMapCoordinates(x=0.5, y=-0.1)


class TestRiskRegisterEntry:
    def _make(self) -> RiskRegisterEntry:
        return RiskRegisterEntry(
            risk_id=uuid.uuid4(),
            category="Schedule",
            description="Critical path delay",
            risk_score=0.36,
            heat_map=HeatMapCoordinates(x=0.6, y=0.6),
            status="OPEN",
        )

    def test_stores_risk_id(self):
        entry = self._make()
        assert isinstance(entry.risk_id, uuid.UUID)

    def test_stores_risk_score(self):
        assert self._make().risk_score == 0.36

    def test_stores_heat_map(self):
        entry = self._make()
        assert isinstance(entry.heat_map, HeatMapCoordinates)

    def test_heat_map_x_is_probability(self):
        entry = self._make()
        assert entry.heat_map.x == 0.6

    def test_is_frozen(self):
        entry = self._make()
        with pytest.raises(FrozenInstanceError):
            entry.status = "CLOSED"  # type: ignore[misc]


class TestRiskPatternMatch:
    def _make(self) -> RiskPatternMatch:
        return RiskPatternMatch(
            pattern_id=uuid.uuid4(),
            pattern_name="Late supplier delivery",
            confidence=0.75,
            historical_outcome="Schedule overrun by 3 weeks",
        )

    def test_stores_pattern_name(self):
        assert self._make().pattern_name == "Late supplier delivery"

    def test_stores_confidence(self):
        assert self._make().confidence == 0.75

    def test_stores_historical_outcome(self):
        assert "overrun" in self._make().historical_outcome

    def test_is_frozen(self):
        with pytest.raises(FrozenInstanceError):
            self._make().confidence = 0.5  # type: ignore[misc]

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            RiskPatternMatch(
                pattern_id=uuid.uuid4(),
                pattern_name="X",
                confidence=1.1,
                historical_outcome="Y",
            )

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            RiskPatternMatch(
                pattern_id=uuid.uuid4(),
                pattern_name="X",
                confidence=-0.1,
                historical_outcome="Y",
            )

    def test_confidence_zero_valid(self):
        m = RiskPatternMatch(
            pattern_id=uuid.uuid4(),
            pattern_name="X",
            confidence=0.0,
            historical_outcome="Y",
        )
        assert m.confidence == 0.0


class TestRiskCreate:
    def test_stores_category(self):
        r = RiskCreate(category="Cost", description="Budget overrun", probability=0.5, impact=0.7)
        assert r.category == "Cost"

    def test_stores_description(self):
        r = RiskCreate(category="Cost", description="Budget overrun", probability=0.5, impact=0.7)
        assert r.description == "Budget overrun"

    def test_probability_below_zero_raises(self):
        with pytest.raises(ValidationError):
            RiskCreate(category="X", description="Y", probability=-0.1, impact=0.5)

    def test_probability_above_one_raises(self):
        with pytest.raises(ValidationError):
            RiskCreate(category="X", description="Y", probability=1.1, impact=0.5)

    def test_impact_below_zero_raises(self):
        with pytest.raises(ValidationError):
            RiskCreate(category="X", description="Y", probability=0.5, impact=-0.1)

    def test_impact_above_one_raises(self):
        with pytest.raises(ValidationError):
            RiskCreate(category="X", description="Y", probability=0.5, impact=1.01)

    def test_boundary_values_valid(self):
        r = RiskCreate(category="X", description="Y", probability=0.0, impact=1.0)
        assert r.probability == 0.0 and r.impact == 1.0


class TestRiskResponse:
    def test_from_attributes_enabled(self):
        assert RiskResponse.model_config.get("from_attributes") is True

    def test_stores_risk_score(self):
        r = RiskResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            category="X", description="Y",
            probability=0.6, impact=0.7, risk_score=0.42, status="OPEN",
        )
        assert r.risk_score == 0.42


class TestRiskAssessmentCreate:
    def test_stores_notes(self):
        a = RiskAssessmentCreate(notes="Analysis", schedule_base=100.0, schedule_std_dev=10.0, cost_base=500_000.0, cost_std_dev=50_000.0)
        assert a.notes == "Analysis"

    def test_schedule_base_zero_raises(self):
        with pytest.raises(ValidationError):
            RiskAssessmentCreate(notes="X", schedule_base=0.0, schedule_std_dev=10.0, cost_base=500_000.0, cost_std_dev=50_000.0)

    def test_negative_std_dev_raises(self):
        with pytest.raises(ValidationError):
            RiskAssessmentCreate(notes="X", schedule_base=100.0, schedule_std_dev=-1.0, cost_base=500_000.0, cost_std_dev=50_000.0)


class TestRiskMitigationCreate:
    def test_stores_action(self):
        m = RiskMitigationCreate(action="Engage backup supplier", owner="PM")
        assert m.action == "Engage backup supplier"

    def test_stores_owner(self):
        m = RiskMitigationCreate(action="Action", owner="John")
        assert m.owner == "John"

    def test_due_date_optional(self):
        m = RiskMitigationCreate(action="Action", owner="PM")
        assert m.due_date is None

    def test_stores_due_date(self):
        d = date(2026, 12, 1)
        m = RiskMitigationCreate(action="Action", owner="PM", due_date=d)
        assert m.due_date == d


class TestMitigationEffectivenessUpdate:
    def test_stores_effectiveness_score(self):
        u = MitigationEffectivenessUpdate(effectiveness_score=0.8)
        assert u.effectiveness_score == 0.8

    def test_score_above_one_raises(self):
        with pytest.raises(ValidationError):
            MitigationEffectivenessUpdate(effectiveness_score=1.1)

    def test_score_below_zero_raises(self):
        with pytest.raises(ValidationError):
            MitigationEffectivenessUpdate(effectiveness_score=-0.1)

    def test_status_optional(self):
        u = MitigationEffectivenessUpdate(effectiveness_score=0.5)
        assert u.status is None
