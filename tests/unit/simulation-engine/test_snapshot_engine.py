"""Tests for PIG snapshot capture — S11-02."""
from unittest.mock import MagicMock

import pytest

from app.simulation.snapshot_engine import capture_pig_snapshot


def _node(ref: str, duration: float = 10.0, cost: float = 1000.0, pct: float = 0.0):
    n = MagicMock()
    n.node_ref = ref
    n.duration_days = duration
    n.cost_estimate = cost
    n.completion_pct = pct
    return n


class TestCaptureEmptyList:
    def test_returns_dict(self):
        result = capture_pig_snapshot([])
        assert isinstance(result, dict)

    def test_has_nodes_key(self):
        assert "nodes" in capture_pig_snapshot([])

    def test_nodes_is_empty_list(self):
        assert capture_pig_snapshot([])["nodes"] == []


class TestCaptureSingleNode:
    def test_nodes_has_one_entry(self):
        result = capture_pig_snapshot([_node("ACT-001")])
        assert len(result["nodes"]) == 1

    def test_node_ref_stored(self):
        result = capture_pig_snapshot([_node("ACT-001")])
        assert result["nodes"][0]["node_ref"] == "ACT-001"

    def test_duration_days_stored(self):
        result = capture_pig_snapshot([_node("X", duration=20.0)])
        assert result["nodes"][0]["duration_days"] == 20.0

    def test_cost_estimate_stored(self):
        result = capture_pig_snapshot([_node("X", cost=5000.0)])
        assert result["nodes"][0]["cost_estimate"] == 5000.0

    def test_completion_pct_stored(self):
        result = capture_pig_snapshot([_node("X", pct=75.0)])
        assert result["nodes"][0]["completion_pct"] == 75.0

    def test_zero_values_stored(self):
        result = capture_pig_snapshot([_node("X", duration=0.0, cost=0.0, pct=0.0)])
        node = result["nodes"][0]
        assert node["duration_days"] == 0.0
        assert node["cost_estimate"] == 0.0


class TestCaptureMultipleNodes:
    def test_all_nodes_captured(self):
        nodes = [_node(f"ACT-{i:03d}") for i in range(5)]
        result = capture_pig_snapshot(nodes)
        assert len(result["nodes"]) == 5

    def test_node_refs_preserved(self):
        nodes = [_node("A"), _node("B"), _node("C")]
        result = capture_pig_snapshot(nodes)
        refs = [n["node_ref"] for n in result["nodes"]]
        assert refs == ["A", "B", "C"]

    def test_each_node_has_all_fields(self):
        result = capture_pig_snapshot([_node("A"), _node("B")])
        for node in result["nodes"]:
            assert "node_ref" in node
            assert "duration_days" in node
            assert "cost_estimate" in node
            assert "completion_pct" in node


class TestMissingAttributes:
    def test_missing_duration_days_defaults_to_zero(self):
        n = MagicMock(spec=["node_ref", "cost_estimate", "completion_pct"])
        n.node_ref = "X"
        n.cost_estimate = 100.0
        n.completion_pct = 0.0
        result = capture_pig_snapshot([n])
        assert result["nodes"][0]["duration_days"] == 0.0

    def test_missing_cost_estimate_defaults_to_zero(self):
        n = MagicMock(spec=["node_ref", "duration_days", "completion_pct"])
        n.node_ref = "X"
        n.duration_days = 5.0
        n.completion_pct = 0.0
        result = capture_pig_snapshot([n])
        assert result["nodes"][0]["cost_estimate"] == 0.0

    def test_none_duration_coerced_to_zero(self):
        n = _node("X")
        n.duration_days = None
        result = capture_pig_snapshot([n])
        assert result["nodes"][0]["duration_days"] == 0.0

    def test_none_cost_coerced_to_zero(self):
        n = _node("X")
        n.cost_estimate = None
        result = capture_pig_snapshot([n])
        assert result["nodes"][0]["cost_estimate"] == 0.0


class TestInputImmutability:
    def test_original_list_not_modified(self):
        nodes = [_node("A"), _node("B")]
        original_len = len(nodes)
        capture_pig_snapshot(nodes)
        assert len(nodes) == original_len
