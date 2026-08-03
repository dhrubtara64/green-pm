"""Tests for forward projection engine — S11-04."""
import uuid

import pytest

from app.simulation.projection_engine import project_impacts
from app.simulation.schemas import ProjectionResult


def _sid() -> uuid.UUID:
    return uuid.uuid4()


def _snapshot(*node_specs) -> dict:
    return {
        "nodes": [
            {
                "node_ref": ref,
                "duration_days": dur,
                "cost_estimate": cost,
                "completion_pct": pct,
            }
            for ref, dur, cost, pct in node_specs
        ]
    }


class TestProjectImpactsReturnType:
    def test_returns_projection_result(self):
        snap = _snapshot(("A", 10.0, 1000.0, 0.0))
        result = project_impacts(_sid(), snap, snap)
        assert isinstance(result, ProjectionResult)

    def test_scenario_id_stored(self):
        sid = _sid()
        snap = _snapshot(("A", 10.0, 1000.0, 0.0))
        result = project_impacts(sid, snap, snap)
        assert result.scenario_id == sid


class TestProjectImpactsNoChanges:
    def test_schedule_delta_zero_when_no_changes(self):
        snap = _snapshot(("A", 10.0, 1000.0, 0.0))
        result = project_impacts(_sid(), snap, snap)
        assert result.schedule_delta_days == 0.0

    def test_budget_delta_zero_when_no_changes(self):
        snap = _snapshot(("A", 10.0, 1000.0, 0.0))
        result = project_impacts(_sid(), snap, snap)
        assert result.budget_delta_pct == 0.0

    def test_affected_count_zero_when_no_changes(self):
        snap = _snapshot(("A", 10.0, 1000.0, 0.0))
        result = project_impacts(_sid(), snap, snap)
        assert result.affected_node_count == 0

    def test_critical_path_not_affected_when_no_changes(self):
        snap = _snapshot(("A", 10.0, 1000.0, 0.0))
        result = project_impacts(_sid(), snap, snap)
        assert result.critical_path_affected is False


class TestProjectImpactsEmptyBaseline:
    def test_empty_baseline_all_zeros(self):
        empty = {"nodes": []}
        result = project_impacts(_sid(), empty, empty)
        assert result.schedule_delta_days == 0.0
        assert result.budget_delta_pct == 0.0
        assert result.affected_node_count == 0


class TestProjectImpactsDurationChange:
    def test_duration_increase_positive_schedule_delta(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0))
        perturbed = _snapshot(("A", 15.0, 1000.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.schedule_delta_days == 5.0

    def test_duration_decrease_negative_schedule_delta(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0))
        perturbed = _snapshot(("A", 7.0, 1000.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.schedule_delta_days == -3.0

    def test_schedule_delta_rounded_to_2dp(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0))
        perturbed = _snapshot(("A", 10.333, 1000.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.schedule_delta_days == round(0.333, 2)

    def test_duration_change_counts_as_affected(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0))
        perturbed = _snapshot(("A", 20.0, 1000.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.affected_node_count == 1


class TestProjectImpactsCostChange:
    def test_cost_increase_positive_budget_delta(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0))
        perturbed = _snapshot(("A", 10.0, 1100.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.budget_delta_pct == 10.0

    def test_cost_decrease_negative_budget_delta(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0))
        perturbed = _snapshot(("A", 10.0, 900.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.budget_delta_pct == -10.0

    def test_budget_delta_rounded_to_4dp(self):
        baseline = _snapshot(("A", 10.0, 3000.0, 0.0))
        perturbed = _snapshot(("A", 10.0, 3001.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.budget_delta_pct == round(1.0 / 3000.0 * 100, 4)

    def test_zero_baseline_cost_gives_zero_budget_delta(self):
        baseline = _snapshot(("A", 10.0, 0.0, 0.0))
        perturbed = _snapshot(("A", 10.0, 500.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.budget_delta_pct == 0.0


class TestProjectImpactsCriticalPath:
    def test_critical_path_affected_when_incomplete_node_duration_changes(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 50.0))
        perturbed = _snapshot(("A", 20.0, 1000.0, 50.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.critical_path_affected is True

    def test_critical_path_not_affected_when_complete_node_duration_changes(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 100.0))
        perturbed = _snapshot(("A", 20.0, 1000.0, 100.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.critical_path_affected is False

    def test_critical_path_not_affected_when_no_nodes_affected(self):
        snap = _snapshot(("A", 10.0, 1000.0, 30.0))
        result = project_impacts(_sid(), snap, snap)
        assert result.critical_path_affected is False


class TestProjectImpactsMultipleNodes:
    def test_multiple_nodes_affected_count(self):
        baseline = _snapshot(
            ("A", 10.0, 1000.0, 0.0),
            ("B", 5.0, 500.0, 0.0),
            ("C", 8.0, 800.0, 0.0),
        )
        perturbed = _snapshot(
            ("A", 15.0, 1000.0, 0.0),
            ("B", 5.0, 600.0, 0.0),
            ("C", 8.0, 800.0, 0.0),
        )
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.affected_node_count == 2

    def test_unaffected_nodes_excluded(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0), ("B", 5.0, 500.0, 0.0))
        perturbed = _snapshot(("A", 10.0, 1000.0, 0.0), ("B", 10.0, 500.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.affected_node_count == 1

    def test_schedule_delta_sums_all_nodes(self):
        baseline = _snapshot(("A", 10.0, 1000.0, 0.0), ("B", 5.0, 500.0, 0.0))
        perturbed = _snapshot(("A", 12.0, 1000.0, 0.0), ("B", 7.0, 500.0, 0.0))
        result = project_impacts(_sid(), baseline, perturbed)
        assert result.schedule_delta_days == 4.0
