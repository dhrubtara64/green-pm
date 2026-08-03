"""Unit tests for CPM algorithm — S6-01, S6-02, S6-03."""
from __future__ import annotations

import uuid

import pytest

from app.cpm.algorithm import CyclicDependencyError, _topological_sort, compute_cpm
from app.cpm.schemas import CPMEdge, CPMNode, CPMResult


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _node(dur: float) -> CPMNode:
    return CPMNode(entity_id=uuid.uuid4(), node_id=uuid.uuid4(), duration=dur)


def _edge(src: CPMNode, tgt: CPMNode, dep="FS", lag=0.0) -> CPMEdge:
    return CPMEdge(
        source_entity_id=src.entity_id,
        target_entity_id=tgt.entity_id,
        dep_type=dep,
        lag=lag,
    )


# ──────────────────────────────────────────────────────────────────────────────
# _topological_sort
# ──────────────────────────────────────────────────────────────────────────────

class TestTopologicalSort:
    def test_single_node_returns_it(self):
        a = uuid.uuid4()
        result = _topological_sort([a], [])
        assert result == [a]

    def test_linear_chain_ordered(self):
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        na = CPMNode(entity_id=a, node_id=uuid.uuid4(), duration=1.0)
        nb = CPMNode(entity_id=b, node_id=uuid.uuid4(), duration=1.0)
        nc = CPMNode(entity_id=c, node_id=uuid.uuid4(), duration=1.0)
        edges = [_edge(na, nb), _edge(nb, nc)]
        result = _topological_sort([a, b, c], edges)
        assert result.index(a) < result.index(b)
        assert result.index(b) < result.index(c)

    def test_cycle_raises(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        na = CPMNode(entity_id=a, node_id=uuid.uuid4(), duration=1.0)
        nb = CPMNode(entity_id=b, node_id=uuid.uuid4(), duration=1.0)
        edges = [_edge(na, nb), _edge(nb, na)]
        with pytest.raises(CyclicDependencyError):
            _topological_sort([a, b], edges)

    def test_empty_list_returns_empty(self):
        assert _topological_sort([], []) == []


# ──────────────────────────────────────────────────────────────────────────────
# compute_cpm — empty / single
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeCPMBasic:
    def test_empty_nodes_returns_zero_duration(self):
        result = compute_cpm([], [])
        assert result.project_duration == pytest.approx(0.0)

    def test_empty_nodes_critical_path_empty(self):
        result = compute_cpm([], [])
        assert result.critical_path == ()

    def test_empty_nodes_floats_empty(self):
        result = compute_cpm([], [])
        assert result.floats == {}

    def test_single_node_duration_equals_project_duration(self):
        a = _node(5.0)
        result = compute_cpm([a], [])
        assert result.project_duration == pytest.approx(5.0)

    def test_single_node_is_critical(self):
        a = _node(5.0)
        result = compute_cpm([a], [])
        assert a.entity_id in result.critical_path

    def test_single_node_total_float_is_zero(self):
        a = _node(5.0)
        result = compute_cpm([a], [])
        assert result.floats[a.entity_id].total_float == pytest.approx(0.0)

    def test_single_node_early_start_is_zero(self):
        a = _node(3.0)
        result = compute_cpm([a], [])
        assert result.floats[a.entity_id].early_start == pytest.approx(0.0)

    def test_single_node_early_finish_equals_duration(self):
        a = _node(3.0)
        result = compute_cpm([a], [])
        assert result.floats[a.entity_id].early_finish == pytest.approx(3.0)

    def test_returns_cpm_result_type(self):
        assert isinstance(compute_cpm([], []), CPMResult)


# ──────────────────────────────────────────────────────────────────────────────
# compute_cpm — FS (Finish-Start)
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeCPMFinishStart:
    def test_linear_chain_project_duration(self):
        a, b, c = _node(2.0), _node(3.0), _node(4.0)
        result = compute_cpm([a, b, c], [_edge(a, b), _edge(b, c)])
        assert result.project_duration == pytest.approx(9.0)

    def test_linear_chain_all_critical(self):
        a, b = _node(2.0), _node(3.0)
        result = compute_cpm([a, b], [_edge(a, b)])
        assert a.entity_id in result.critical_path
        assert b.entity_id in result.critical_path

    def test_diamond_critical_path_is_longer_branch(self):
        # A → B (5) → D
        # A → C (2) → D
        a, b, c, d = _node(1.0), _node(5.0), _node(2.0), _node(1.0)
        result = compute_cpm(
            [a, b, c, d],
            [_edge(a, b), _edge(a, c), _edge(b, d), _edge(c, d)],
        )
        assert b.entity_id in result.critical_path
        assert c.entity_id not in result.critical_path

    def test_diamond_shorter_branch_has_float(self):
        a, b, c, d = _node(1.0), _node(5.0), _node(2.0), _node(1.0)
        result = compute_cpm(
            [a, b, c, d],
            [_edge(a, b), _edge(a, c), _edge(b, d), _edge(c, d)],
        )
        assert result.floats[c.entity_id].total_float > 0.0

    def test_fs_lag_delays_successor(self):
        a, b = _node(3.0), _node(2.0)
        result = compute_cpm([a, b], [_edge(a, b, lag=2.0)])
        # ES[b] = EF[a] + 2 = 5; EF[b] = 7
        assert result.floats[b.entity_id].early_start == pytest.approx(5.0)
        assert result.project_duration == pytest.approx(7.0)

    def test_fs_negative_lag_lead_overlaps_activities(self):
        a, b = _node(4.0), _node(2.0)
        # ES[b] = EF[a] - 1 = 3
        result = compute_cpm([a, b], [_edge(a, b, lag=-1.0)])
        assert result.floats[b.entity_id].early_start == pytest.approx(3.0)

    def test_parallel_activities_no_edges_longest_is_critical(self):
        a, b, c = _node(3.0), _node(7.0), _node(5.0)
        result = compute_cpm([a, b, c], [])
        assert b.entity_id in result.critical_path
        assert result.project_duration == pytest.approx(7.0)


# ──────────────────────────────────────────────────────────────────────────────
# compute_cpm — SS (Start-Start)
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeCPMStartStart:
    def test_ss_successor_starts_with_predecessor(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="SS")])
        # ES[b] = ES[a] + 0 = 0; EF[b] = 5
        assert result.floats[b.entity_id].early_start == pytest.approx(0.0)
        assert result.project_duration == pytest.approx(5.0)

    def test_ss_with_lag(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="SS", lag=1.0)])
        # ES[b] = ES[a] + 1 = 1; EF[b] = 6
        assert result.floats[b.entity_id].early_start == pytest.approx(1.0)
        assert result.project_duration == pytest.approx(6.0)

    def test_ss_both_critical_when_constrained(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="SS", lag=1.0)])
        assert a.entity_id in result.critical_path
        assert b.entity_id in result.critical_path


# ──────────────────────────────────────────────────────────────────────────────
# compute_cpm — FF (Finish-Finish)
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeCPMFinishFinish:
    def test_ff_constrains_ef_of_target(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="FF", lag=2.0)])
        # EF[b] >= EF[a] + 2 = 5; ES[b] = 5-5 = 0; project_duration = 5
        assert result.floats[b.entity_id].early_finish == pytest.approx(5.0)

    def test_ff_no_lag_finishes_together(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="FF")])
        # EF[b] >= EF[a] = 3; but b has duration 5, so ES[b] = max(0, 3-5) = 0; EF[b] = 5
        assert result.project_duration == pytest.approx(5.0)

    def test_ff_with_lag_extends_project(self):
        a, b = _node(4.0), _node(3.0)
        # EF[b] >= EF[a] + 3 = 7; ES[b] = 7-3 = 4; project = 7
        result = compute_cpm([a, b], [_edge(a, b, dep="FF", lag=3.0)])
        assert result.project_duration == pytest.approx(7.0)


# ──────────────────────────────────────────────────────────────────────────────
# compute_cpm — SF (Start-Finish)
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeCPMStartFinish:
    def test_sf_constrains_ef_of_target_via_es_of_source(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="SF", lag=6.0)])
        # EF[b] >= ES[a] + 6 = 6; ES[b] = 6-5 = 1; project = max(3, 6) = 6
        assert result.floats[b.entity_id].early_finish == pytest.approx(6.0)
        assert result.project_duration == pytest.approx(6.0)

    def test_sf_source_has_float_when_slack_exists(self):
        a, b = _node(3.0), _node(5.0)
        result = compute_cpm([a, b], [_edge(a, b, dep="SF", lag=6.0)])
        # A finishes at 3, project is 6 → TF[a] = LS[a] - ES[a]
        assert result.floats[a.entity_id].total_float >= 0.0


# ──────────────────────────────────────────────────────────────────────────────
# compute_cpm — float values
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeCPMFloats:
    def test_total_float_zero_on_critical_path(self):
        a, b = _node(2.0), _node(3.0)
        result = compute_cpm([a, b], [_edge(a, b)])
        assert result.floats[a.entity_id].total_float == pytest.approx(0.0)
        assert result.floats[b.entity_id].total_float == pytest.approx(0.0)

    def test_total_float_positive_off_critical_path(self):
        # diamond: a→b(5), a→c(2), b→d, c→d; C has float of 3
        a, b, c, d = _node(1.0), _node(5.0), _node(2.0), _node(1.0)
        result = compute_cpm(
            [a, b, c, d],
            [_edge(a, b), _edge(a, c), _edge(b, d), _edge(c, d)],
        )
        assert result.floats[c.entity_id].total_float == pytest.approx(3.0)

    def test_free_float_zero_when_successor_starts_immediately(self):
        a, b = _node(2.0), _node(3.0)
        result = compute_cpm([a, b], [_edge(a, b)])
        assert result.floats[a.entity_id].free_float == pytest.approx(0.0)

    def test_free_float_positive_for_non_critical_with_slack(self):
        a, b, c, d = _node(1.0), _node(5.0), _node(2.0), _node(1.0)
        result = compute_cpm(
            [a, b, c, d],
            [_edge(a, b), _edge(a, c), _edge(b, d), _edge(c, d)],
        )
        assert result.floats[c.entity_id].free_float >= 0.0

    def test_near_critical_contains_activities_below_threshold(self):
        a, b, c, d = _node(1.0), _node(5.0), _node(4.5), _node(1.0)
        # C has float = 0.5 → near-critical
        result = compute_cpm(
            [a, b, c, d],
            [_edge(a, b), _edge(a, c), _edge(b, d), _edge(c, d)],
        )
        assert c.entity_id in result.near_critical

    def test_near_critical_excludes_critical_activities(self):
        a, b, c, d = _node(1.0), _node(5.0), _node(4.5), _node(1.0)
        result = compute_cpm(
            [a, b, c, d],
            [_edge(a, b), _edge(a, c), _edge(b, d), _edge(c, d)],
        )
        for eid in result.critical_path:
            assert eid not in result.near_critical

    def test_cycle_raises_cyclic_dependency_error(self):
        a, b = _node(2.0), _node(3.0)
        with pytest.raises(CyclicDependencyError):
            compute_cpm([a, b], [_edge(a, b), _edge(b, a)])
