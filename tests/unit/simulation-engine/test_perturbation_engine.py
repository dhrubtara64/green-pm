"""Tests for perturbation application engine — S11-03."""
import pytest

from app.simulation.perturbation_engine import (
    NodeNotFoundError,
    apply_all_perturbations,
    apply_perturbation,
)
from app.simulation.schemas import PerturbationSpec


def _snapshot(*node_specs) -> dict:
    return {
        "nodes": [
            {"node_ref": ref, "duration_days": dur, "cost_estimate": cost, "completion_pct": pct}
            for ref, dur, cost, pct in node_specs
        ]
    }


def _spec(ref: str, field: str = "duration_days",
          original: float = 10.0, perturbed: float = 15.0) -> PerturbationSpec:
    return PerturbationSpec(node_ref=ref, field=field,
                            original_value=original, perturbed_value=perturbed)


class TestApplyPerturbation:
    def test_returns_dict(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_perturbation(snap, _spec("ACT-001"))
        assert isinstance(result, dict)

    def test_target_field_updated(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_perturbation(snap, _spec("ACT-001", "duration_days", 10.0, 20.0))
        assert result["nodes"][0]["duration_days"] == 20.0

    def test_other_fields_unchanged(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 50.0))
        result = apply_perturbation(snap, _spec("ACT-001", "duration_days", 10.0, 20.0))
        node = result["nodes"][0]
        assert node["cost_estimate"] == 1000.0
        assert node["completion_pct"] == 50.0

    def test_other_nodes_unchanged(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0), ("ACT-002", 5.0, 500.0, 0.0))
        result = apply_perturbation(snap, _spec("ACT-001", "duration_days", 10.0, 20.0))
        assert result["nodes"][1]["duration_days"] == 5.0

    def test_node_not_found_raises(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        with pytest.raises(NodeNotFoundError):
            apply_perturbation(snap, _spec("ACT-999"))

    def test_error_message_contains_node_ref(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        with pytest.raises(NodeNotFoundError, match="ACT-999"):
            apply_perturbation(snap, _spec("ACT-999"))

    def test_input_snapshot_not_mutated(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        original_dur = snap["nodes"][0]["duration_days"]
        apply_perturbation(snap, _spec("ACT-001", "duration_days", 10.0, 20.0))
        assert snap["nodes"][0]["duration_days"] == original_dur

    def test_returns_new_dict(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_perturbation(snap, _spec("ACT-001"))
        assert result is not snap

    def test_cost_estimate_field(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_perturbation(snap, _spec("ACT-001", "cost_estimate", 1000.0, 1500.0))
        assert result["nodes"][0]["cost_estimate"] == 1500.0

    def test_completion_pct_field(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_perturbation(snap, _spec("ACT-001", "completion_pct", 0.0, 50.0))
        assert result["nodes"][0]["completion_pct"] == 50.0

    def test_empty_snapshot_raises(self):
        snap = {"nodes": []}
        with pytest.raises(NodeNotFoundError):
            apply_perturbation(snap, _spec("ACT-001"))


class TestApplyAllPerturbations:
    def test_empty_specs_returns_equivalent_snapshot(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_all_perturbations(snap, [])
        assert result["nodes"][0]["duration_days"] == 10.0

    def test_single_spec_applied(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        result = apply_all_perturbations(snap, [_spec("ACT-001", "duration_days", 10.0, 18.0)])
        assert result["nodes"][0]["duration_days"] == 18.0

    def test_multiple_specs_applied_in_order(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0), ("ACT-002", 5.0, 500.0, 0.0))
        specs = [
            _spec("ACT-001", "duration_days", 10.0, 20.0),
            _spec("ACT-002", "cost_estimate", 500.0, 750.0),
        ]
        result = apply_all_perturbations(snap, specs)
        assert result["nodes"][0]["duration_days"] == 20.0
        assert result["nodes"][1]["cost_estimate"] == 750.0

    def test_first_spec_failure_raises(self):
        snap = _snapshot(("ACT-001", 10.0, 1000.0, 0.0))
        specs = [_spec("MISSING", "duration_days", 10.0, 15.0)]
        with pytest.raises(NodeNotFoundError):
            apply_all_perturbations(snap, specs)
