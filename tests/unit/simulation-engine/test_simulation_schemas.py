"""Tests for Simulation Engine domain and API schemas — S11-01, S11-05."""
import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.simulation.schemas import (
    PerturbationCreate,
    PerturbationField,
    PerturbationSpec,
    ProjectionResult,
    ScenarioCreate,
    ScenarioPerturbationResponse,
    ScenarioProjectionResponse,
    ScenarioResponse,
    _PERTURBATION_FIELDS,
    _SCENARIO_STATUSES,
)


class TestScenarioStatusesConstant:
    def test_is_frozenset(self):
        assert isinstance(_SCENARIO_STATUSES, frozenset)

    def test_has_three_values(self):
        assert len(_SCENARIO_STATUSES) == 3

    def test_draft_present(self):
        assert "DRAFT" in _SCENARIO_STATUSES

    def test_active_present(self):
        assert "ACTIVE" in _SCENARIO_STATUSES

    def test_archived_present(self):
        assert "ARCHIVED" in _SCENARIO_STATUSES


class TestPerturbationFieldsConstant:
    def test_is_frozenset(self):
        assert isinstance(_PERTURBATION_FIELDS, frozenset)

    def test_has_three_fields(self):
        assert len(_PERTURBATION_FIELDS) == 3

    def test_duration_days_present(self):
        assert "duration_days" in _PERTURBATION_FIELDS

    def test_cost_estimate_present(self):
        assert "cost_estimate" in _PERTURBATION_FIELDS

    def test_completion_pct_present(self):
        assert "completion_pct" in _PERTURBATION_FIELDS


class TestPerturbationSpec:
    def _make(self, **overrides) -> PerturbationSpec:
        base = dict(
            node_ref="ACT-001",
            field="duration_days",
            original_value=10.0,
            perturbed_value=15.0,
        )
        return PerturbationSpec(**{**base, **overrides})

    def test_stores_node_ref(self):
        assert self._make().node_ref == "ACT-001"

    def test_stores_field(self):
        assert self._make().field == "duration_days"

    def test_stores_original_value(self):
        assert self._make().original_value == 10.0

    def test_stores_perturbed_value(self):
        assert self._make().perturbed_value == 15.0

    def test_is_frozen(self):
        spec = self._make()
        with pytest.raises(FrozenInstanceError):
            spec.node_ref = "OTHER"  # type: ignore[misc]

    def test_empty_node_ref_raises(self):
        with pytest.raises(ValueError, match="node_ref"):
            self._make(node_ref="")

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="perturbation fields"):
            self._make(field="bogus_field")

    def test_duration_days_valid(self):
        spec = self._make(field="duration_days")
        assert spec.field == "duration_days"

    def test_cost_estimate_valid(self):
        spec = self._make(field="cost_estimate")
        assert spec.field == "cost_estimate"

    def test_completion_pct_valid(self):
        spec = self._make(field="completion_pct")
        assert spec.field == "completion_pct"

    def test_zero_original_value_valid(self):
        spec = self._make(original_value=0.0)
        assert spec.original_value == 0.0

    def test_negative_perturbed_value_valid(self):
        spec = self._make(perturbed_value=-5.0)
        assert spec.perturbed_value == -5.0


class TestProjectionResult:
    def _make(self, **overrides) -> ProjectionResult:
        sid = uuid.uuid4()
        base = dict(
            scenario_id=sid,
            schedule_delta_days=5.0,
            budget_delta_pct=2.5,
            affected_node_count=3,
            critical_path_affected=True,
        )
        return ProjectionResult(**{**base, **overrides})

    def test_stores_scenario_id(self):
        sid = uuid.uuid4()
        r = self._make(scenario_id=sid)
        assert r.scenario_id == sid

    def test_stores_schedule_delta_days(self):
        assert self._make().schedule_delta_days == 5.0

    def test_stores_budget_delta_pct(self):
        assert self._make().budget_delta_pct == 2.5

    def test_stores_affected_node_count(self):
        assert self._make().affected_node_count == 3

    def test_stores_critical_path_affected_true(self):
        assert self._make().critical_path_affected is True

    def test_stores_critical_path_affected_false(self):
        assert self._make(critical_path_affected=False).critical_path_affected is False

    def test_is_frozen(self):
        r = self._make()
        with pytest.raises(FrozenInstanceError):
            r.schedule_delta_days = 0.0  # type: ignore[misc]

    def test_negative_affected_node_count_raises(self):
        with pytest.raises(ValueError, match="affected_node_count"):
            self._make(affected_node_count=-1)

    def test_zero_affected_node_count_valid(self):
        r = self._make(affected_node_count=0)
        assert r.affected_node_count == 0

    def test_negative_schedule_delta_valid(self):
        r = self._make(schedule_delta_days=-3.0)
        assert r.schedule_delta_days == -3.0

    def test_negative_budget_delta_valid(self):
        r = self._make(budget_delta_pct=-1.5)
        assert r.budget_delta_pct == -1.5

    def test_zero_deltas_valid(self):
        r = self._make(schedule_delta_days=0.0, budget_delta_pct=0.0)
        assert r.schedule_delta_days == 0.0
        assert r.budget_delta_pct == 0.0


class TestScenarioCreate:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        s = ScenarioCreate(project_id=pid, name="Base case")
        assert s.project_id == pid

    def test_stores_name(self):
        s = ScenarioCreate(project_id=uuid.uuid4(), name="Delay scenario")
        assert s.name == "Delay scenario"

    def test_description_optional_none(self):
        s = ScenarioCreate(project_id=uuid.uuid4(), name="X")
        assert s.description is None

    def test_description_stored(self):
        s = ScenarioCreate(project_id=uuid.uuid4(), name="X", description="Test desc")
        assert s.description == "Test desc"


class TestScenarioResponse:
    def test_from_attributes_enabled(self):
        assert ScenarioResponse.model_config.get("from_attributes") is True

    def test_stores_status(self):
        r = ScenarioResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            name="S", status="DRAFT"
        )
        assert r.status == "DRAFT"

    def test_created_at_optional(self):
        r = ScenarioResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            name="S", status="ACTIVE"
        )
        assert r.created_at is None

    def test_description_optional(self):
        r = ScenarioResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            name="S", status="DRAFT"
        )
        assert r.description is None


class TestPerturbationCreate:
    def test_stores_node_ref(self):
        p = PerturbationCreate(node_ref="ACT-001", field="duration_days",
                               original_value=10.0, perturbed_value=15.0)
        assert p.node_ref == "ACT-001"

    def test_stores_field(self):
        p = PerturbationCreate(node_ref="X", field="cost_estimate",
                               original_value=1000.0, perturbed_value=1200.0)
        assert p.field == "cost_estimate"

    def test_invalid_field_raises(self):
        with pytest.raises(ValidationError):
            PerturbationCreate(node_ref="X", field="bogus",  # type: ignore[arg-type]
                               original_value=1.0, perturbed_value=2.0)

    def test_all_valid_fields_accepted(self):
        for f in _PERTURBATION_FIELDS:
            p = PerturbationCreate(node_ref="X", field=f,  # type: ignore[arg-type]
                                   original_value=1.0, perturbed_value=2.0)
            assert p.field == f


class TestScenarioPerturbationResponse:
    def test_from_attributes_enabled(self):
        assert ScenarioPerturbationResponse.model_config.get("from_attributes") is True

    def test_stores_fields(self):
        r = ScenarioPerturbationResponse(
            id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            node_ref="ACT-002", field="duration_days",
            original_value=5.0, perturbed_value=8.0,
        )
        assert r.node_ref == "ACT-002"
        assert r.original_value == 5.0


class TestScenarioProjectionResponse:
    def test_from_attributes_enabled(self):
        assert ScenarioProjectionResponse.model_config.get("from_attributes") is True

    def test_stores_schedule_delta(self):
        r = ScenarioProjectionResponse(
            id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            schedule_delta_days=7.5, budget_delta_pct=3.2,
        )
        assert r.schedule_delta_days == 7.5

    def test_critical_path_changes_optional(self):
        r = ScenarioProjectionResponse(
            id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            schedule_delta_days=0.0, budget_delta_pct=0.0,
        )
        assert r.critical_path_changes is None

    def test_projected_at_optional(self):
        r = ScenarioProjectionResponse(
            id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            schedule_delta_days=0.0, budget_delta_pct=0.0,
        )
        assert r.projected_at is None
