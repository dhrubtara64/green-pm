"""Tests for Readiness Engine domain and API schemas — S10-01–S10-05."""
import uuid
from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.readiness.schemas import (
    CriterionStatusUpdate,
    GateComputationResult,
    GateType,
    ReadinessCriterionCreate,
    ReadinessCriterionResponse,
    ReadinessGateCreate,
    ReadinessGateResponse,
    ReadinessScoreResponse,
    _CRITERIA_STATUSES,
    _GATE_STATUSES,
    _GATE_TYPES,
)


class TestGateTypesConstant:
    def test_has_six_gate_types(self):
        assert len(_GATE_TYPES) == 6

    def test_engineering_first(self):
        assert _GATE_TYPES[0] == "ENGINEERING"

    def test_cod_last(self):
        assert _GATE_TYPES[-1] == "COD"

    def test_all_types_present(self):
        expected = {"ENGINEERING", "MATERIAL", "CONSTRUCTION", "QUALITY", "COMMISSIONING", "COD"}
        assert set(_GATE_TYPES) == expected

    def test_is_tuple(self):
        assert isinstance(_GATE_TYPES, tuple)


class TestGateStatusesConstant:
    def test_has_four_statuses(self):
        assert len(_GATE_STATUSES) == 4

    def test_not_started_present(self):
        assert "NOT_STARTED" in _GATE_STATUSES

    def test_in_progress_present(self):
        assert "IN_PROGRESS" in _GATE_STATUSES

    def test_ready_present(self):
        assert "READY" in _GATE_STATUSES

    def test_blocked_present(self):
        assert "BLOCKED" in _GATE_STATUSES

    def test_is_frozenset(self):
        assert isinstance(_GATE_STATUSES, frozenset)


class TestCriteriaStatusesConstant:
    def test_has_three_statuses(self):
        assert len(_CRITERIA_STATUSES) == 3

    def test_pending_present(self):
        assert "PENDING" in _CRITERIA_STATUSES

    def test_met_present(self):
        assert "MET" in _CRITERIA_STATUSES

    def test_waived_present(self):
        assert "WAIVED" in _CRITERIA_STATUSES

    def test_is_frozenset(self):
        assert isinstance(_CRITERIA_STATUSES, frozenset)


class TestGateComputationResult:
    def _make(self, **overrides) -> GateComputationResult:
        base = dict(
            gate_type="ENGINEERING",
            total_criteria=10,
            met_criteria=5,
            waived_criteria=2,
            pending_criteria=3,
            completion_percentage=70.0,
            status="IN_PROGRESS",
        )
        return GateComputationResult(**{**base, **overrides})

    def test_stores_gate_type(self):
        assert self._make().gate_type == "ENGINEERING"

    def test_stores_total(self):
        assert self._make().total_criteria == 10

    def test_stores_met(self):
        assert self._make().met_criteria == 5

    def test_stores_waived(self):
        assert self._make().waived_criteria == 2

    def test_stores_pending(self):
        assert self._make().pending_criteria == 3

    def test_stores_completion_percentage(self):
        assert self._make().completion_percentage == 70.0

    def test_stores_status(self):
        assert self._make().status == "IN_PROGRESS"

    def test_is_frozen(self):
        r = self._make()
        with pytest.raises(FrozenInstanceError):
            r.status = "READY"  # type: ignore[misc]

    def test_invalid_gate_type_raises(self):
        with pytest.raises(ValueError, match="gate_type"):
            self._make(gate_type="INVALID")

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="gate status"):
            self._make(status="UNKNOWN")

    def test_completion_above_100_raises(self):
        with pytest.raises(ValueError, match="completion_percentage"):
            self._make(completion_percentage=101.0)

    def test_completion_below_zero_raises(self):
        with pytest.raises(ValueError, match="completion_percentage"):
            self._make(completion_percentage=-1.0)

    def test_all_gate_types_valid(self):
        for gt in _GATE_TYPES:
            r = self._make(gate_type=gt)
            assert r.gate_type == gt


class TestReadinessGateCreate:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        g = ReadinessGateCreate(project_id=pid, gate_type="ENGINEERING")
        assert g.project_id == pid

    def test_stores_gate_type(self):
        g = ReadinessGateCreate(project_id=uuid.uuid4(), gate_type="MATERIAL")
        assert g.gate_type == "MATERIAL"

    def test_invalid_gate_type_raises(self):
        with pytest.raises(ValidationError):
            ReadinessGateCreate(project_id=uuid.uuid4(), gate_type="INVALID")

    def test_all_valid_gate_types_accepted(self):
        for gt in _GATE_TYPES:
            g = ReadinessGateCreate(project_id=uuid.uuid4(), gate_type=gt)  # type: ignore[arg-type]
            assert g.gate_type == gt


class TestReadinessGateResponse:
    def test_from_attributes_enabled(self):
        assert ReadinessGateResponse.model_config.get("from_attributes") is True

    def test_stores_status(self):
        r = ReadinessGateResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            gate_type="QUALITY", status="IN_PROGRESS", completion_percentage=50.0
        )
        assert r.status == "IN_PROGRESS"

    def test_created_at_optional(self):
        r = ReadinessGateResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            gate_type="COD", status="NOT_STARTED", completion_percentage=0.0
        )
        assert r.created_at is None


class TestReadinessCriterionCreate:
    def test_stores_title(self):
        c = ReadinessCriterionCreate(
            gate_id=uuid.uuid4(), gate_type="ENGINEERING", title="Approved drawings"
        )
        assert c.title == "Approved drawings"

    def test_stores_gate_type(self):
        c = ReadinessCriterionCreate(
            gate_id=uuid.uuid4(), gate_type="COMMISSIONING", title="X"
        )
        assert c.gate_type == "COMMISSIONING"

    def test_description_optional(self):
        c = ReadinessCriterionCreate(gate_id=uuid.uuid4(), gate_type="MATERIAL", title="X")
        assert c.description is None

    def test_responsible_party_optional(self):
        c = ReadinessCriterionCreate(gate_id=uuid.uuid4(), gate_type="MATERIAL", title="X")
        assert c.responsible_party is None

    def test_due_date_optional(self):
        c = ReadinessCriterionCreate(gate_id=uuid.uuid4(), gate_type="MATERIAL", title="X")
        assert c.due_date is None

    def test_stores_due_date(self):
        d = date(2026, 12, 1)
        c = ReadinessCriterionCreate(gate_id=uuid.uuid4(), gate_type="QUALITY", title="X", due_date=d)
        assert c.due_date == d

    def test_invalid_gate_type_raises(self):
        with pytest.raises(ValidationError):
            ReadinessCriterionCreate(gate_id=uuid.uuid4(), gate_type="BOGUS", title="X")  # type: ignore[arg-type]


class TestCriterionStatusUpdate:
    def test_stores_status_met(self):
        u = CriterionStatusUpdate(status="MET")
        assert u.status == "MET"

    def test_stores_status_waived(self):
        u = CriterionStatusUpdate(status="WAIVED")
        assert u.status == "WAIVED"

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            CriterionStatusUpdate(status="INVALID")  # type: ignore[arg-type]


class TestReadinessScoreResponse:
    def test_from_attributes_enabled(self):
        assert ReadinessScoreResponse.model_config.get("from_attributes") is True

    def test_stores_completion_percentage(self):
        r = ReadinessScoreResponse(
            id=uuid.uuid4(), gate_id=uuid.uuid4(),
            gate_type="CONSTRUCTION", total_criteria=10,
            met_criteria=8, waived_criteria=1, completion_percentage=90.0
        )
        assert r.completion_percentage == 90.0
