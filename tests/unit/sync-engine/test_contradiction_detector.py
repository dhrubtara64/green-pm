"""Tests for Synchronization & Consistency Engine contradiction detector — S15-06."""
import uuid

import pytest

from app.sync.detector import _generate_recommendation, detect_contradictions
from app.sync.schemas import INCONSISTENCY_THRESHOLD, InconsistencyResult


def _edge(a: uuid.UUID, b: uuid.UUID, edge_type: str, weight: float) -> dict:
    return {"entity_a_id": a, "entity_b_id": b, "edge_type": edge_type, "weight": weight}


class TestGenerateRecommendation:
    def test_returns_string(self):
        r = _generate_recommendation("dep", 0.6, 0.2, 0.8)
        assert isinstance(r, str)

    def test_contains_edge_type(self):
        r = _generate_recommendation("impact", 0.5, 0.3, 0.8)
        assert "impact" in r

    def test_contains_delta(self):
        r = _generate_recommendation("dep", 0.6, 0.2, 0.8)
        assert "0.600" in r or "0.6" in r

    def test_non_empty(self):
        assert len(_generate_recommendation("dep", 0.5, 0.2, 0.7)) > 0


class TestDetectContradictions:
    def test_empty_edges_returns_empty(self):
        assert detect_contradictions([]) == []

    def test_single_edge_returns_empty(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        assert detect_contradictions([_edge(a, b, "dep", 0.5)]) == []

    def test_two_edges_same_pair_within_threshold_not_flagged(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.3), _edge(a, b, "dep", 0.4)]
        # delta = 0.1 <= 0.2 threshold
        assert detect_contradictions(edges) == []

    def test_two_edges_same_pair_at_threshold_not_flagged(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.3), _edge(a, b, "dep", 0.5)]
        # delta = 0.2 == threshold, NOT flagged (delta <= threshold)
        assert detect_contradictions(edges) == []

    def test_two_edges_same_pair_above_threshold_flagged(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.2), _edge(a, b, "dep", 0.9)]
        # delta = 0.7 > 0.2
        result = detect_contradictions(edges)
        assert len(result) == 1

    def test_returns_inconsistency_result_objects(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.1), _edge(a, b, "dep", 0.9)]
        result = detect_contradictions(edges)
        assert all(isinstance(r, InconsistencyResult) for r in result)

    def test_entity_ids_preserved(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.1), _edge(a, b, "dep", 0.9)]
        result = detect_contradictions(edges)
        assert result[0].entity_a_id == a
        assert result[0].entity_b_id == b

    def test_edge_type_preserved(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "critical_path", 0.1), _edge(a, b, "critical_path", 0.9)]
        result = detect_contradictions(edges)
        assert result[0].edge_type == "critical_path"

    def test_weight_a_is_minimum(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.8), _edge(a, b, "dep", 0.1)]
        result = detect_contradictions(edges)
        assert result[0].weight_a == pytest.approx(0.1)

    def test_weight_b_is_maximum(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.8), _edge(a, b, "dep", 0.1)]
        result = detect_contradictions(edges)
        assert result[0].weight_b == pytest.approx(0.8)

    def test_delta_computed_correctly(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.2), _edge(a, b, "dep", 0.9)]
        result = detect_contradictions(edges)
        assert result[0].delta == pytest.approx(0.7)

    def test_recommendation_is_non_empty_string(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [_edge(a, b, "dep", 0.1), _edge(a, b, "dep", 0.9)]
        result = detect_contradictions(edges)
        assert isinstance(result[0].recommendation, str)
        assert len(result[0].recommendation) > 0

    def test_different_edge_types_not_grouped(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        # dep: 0.1 only one edge, impact: 0.9 only one edge
        edges = [_edge(a, b, "dep", 0.1), _edge(a, b, "impact", 0.9)]
        assert detect_contradictions(edges) == []

    def test_different_entity_pairs_not_grouped(self):
        a, b, c, d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        # (a,b) and (c,d) are different pairs
        edges = [_edge(a, b, "dep", 0.1), _edge(c, d, "dep", 0.9)]
        assert detect_contradictions(edges) == []

    def test_multiple_contradictions_all_detected(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        c, d = uuid.uuid4(), uuid.uuid4()
        edges = [
            _edge(a, b, "dep", 0.1), _edge(a, b, "dep", 0.9),   # delta=0.8
            _edge(c, d, "dep", 0.2), _edge(c, d, "dep", 0.9),   # delta=0.7
        ]
        result = detect_contradictions(edges)
        assert len(result) == 2

    def test_sorted_by_delta_descending(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        c, d = uuid.uuid4(), uuid.uuid4()
        edges = [
            _edge(a, b, "dep", 0.3), _edge(a, b, "dep", 0.8),   # delta=0.5
            _edge(c, d, "dep", 0.1), _edge(c, d, "dep", 0.9),   # delta=0.8
        ]
        result = detect_contradictions(edges)
        assert len(result) == 2
        assert result[0].delta > result[1].delta

    def test_custom_threshold_respected(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        # delta=0.3, default threshold 0.2 → flagged; custom threshold 0.4 → not flagged
        edges = [_edge(a, b, "dep", 0.3), _edge(a, b, "dep", 0.6)]
        assert len(detect_contradictions(edges, threshold=0.4)) == 0
        assert len(detect_contradictions(edges, threshold=0.2)) == 1

    def test_edges_missing_entity_ids_skipped(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [
            {"entity_a_id": None, "entity_b_id": b, "edge_type": "dep", "weight": 0.1},
            _edge(a, b, "dep", 0.9),
        ]
        # Only valid edge, group size < 2
        assert detect_contradictions(edges) == []

    def test_three_edges_uses_min_max(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [
            _edge(a, b, "dep", 0.1),
            _edge(a, b, "dep", 0.5),
            _edge(a, b, "dep", 0.9),
        ]
        result = detect_contradictions(edges)
        assert len(result) == 1
        assert result[0].weight_a == pytest.approx(0.1)
        assert result[0].weight_b == pytest.approx(0.9)
        assert result[0].delta == pytest.approx(0.8)
