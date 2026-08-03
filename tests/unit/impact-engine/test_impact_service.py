"""Unit tests for Impact quantification service — S5-02, S5-04."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.impact.service import (
    _QUALITY_ENTITY_TYPES,
    _REGULATORY_ENTITY_TYPES,
    _SAFETY_ENTITY_TYPES,
    _generate_narrative,
    quantify_impact,
)
from app.impact.schemas import ImpactDimension, ImpactResult, _IMPACT_DIMENSIONS
from app.traversal.pig_traversal import TraversalResult

_ENTITY_ID = uuid.uuid4()


def _make_node(entity_type="activity"):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.entity_type = entity_type
    m.entity_id = uuid.uuid4()
    return m


def _make_edge(source_id=None, target_id=None, edge_type="BLOCKS", weight=1.0):
    m = MagicMock()
    m.source_node_id = source_id or uuid.uuid4()
    m.target_node_id = target_id or uuid.uuid4()
    m.edge_type = edge_type
    m.weight = weight
    return m


def _make_traversal(affected=(), edges=(), hops=0) -> TraversalResult:
    return TraversalResult(
        start_entity_type="activity",
        start_entity_id=_ENTITY_ID,
        affected_nodes=tuple(affected),
        edges_traversed=tuple(edges),
        hops_reached=hops,
    )


# ──────────────────────────────────────────────────────────────────────────────
# quantify_impact — empty traversal
# ──────────────────────────────────────────────────────────────────────────────

class TestQuantifyImpactEmpty:
    def test_all_6_dimensions_present_on_empty(self):
        result = quantify_impact(_make_traversal())
        for dim in _IMPACT_DIMENSIONS:
            assert dim in result.dimensions

    def test_all_dimensions_zero_on_empty(self):
        result = quantify_impact(_make_traversal())
        for dim_obj in result.dimensions.values():
            assert dim_obj.value == pytest.approx(0.0)

    def test_all_confidence_zero_on_empty(self):
        result = quantify_impact(_make_traversal())
        for dim_obj in result.dimensions.values():
            assert dim_obj.confidence_score == pytest.approx(0.0)

    def test_affected_entity_count_is_zero(self):
        result = quantify_impact(_make_traversal())
        assert result.affected_entity_count == 0

    def test_narrative_says_no_impact_when_empty(self):
        result = quantify_impact(_make_traversal())
        assert "no cascading impact" in result.narrative_summary


# ──────────────────────────────────────────────────────────────────────────────
# quantify_impact — scope dimension
# ──────────────────────────────────────────────────────────────────────────────

class TestScopeDimension:
    def test_scope_value_equals_affected_node_count(self):
        nodes = [_make_node() for _ in range(4)]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["scope"].value == pytest.approx(4.0)

    def test_scope_confidence_nonzero_when_nodes_present(self):
        nodes = [_make_node() for _ in range(3)]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["scope"].confidence_score > 0.0

    def test_scope_confidence_capped_at_1(self):
        nodes = [_make_node() for _ in range(15)]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["scope"].confidence_score <= 1.0


# ──────────────────────────────────────────────────────────────────────────────
# quantify_impact — schedule dimension
# ──────────────────────────────────────────────────────────────────────────────

class TestScheduleDimension:
    def test_schedule_is_sum_of_blocks_edge_weights(self):
        edges = [
            _make_edge(edge_type="BLOCKS", weight=2.5),
            _make_edge(edge_type="BLOCKS", weight=1.5),
        ]
        nodes = [_make_node()]
        result = quantify_impact(_make_traversal(affected=nodes, edges=edges, hops=1))
        assert result.dimensions["schedule"].value == pytest.approx(4.0)

    def test_non_blocks_edges_do_not_add_to_schedule(self):
        edges = [
            _make_edge(edge_type="IMPACTS", weight=3.0),
            _make_edge(edge_type="BLOCKS", weight=1.0),
        ]
        nodes = [_make_node()]
        result = quantify_impact(_make_traversal(affected=nodes, edges=edges, hops=1))
        assert result.dimensions["schedule"].value == pytest.approx(1.0)

    def test_schedule_confidence_nonzero_when_blocks_exist(self):
        edges = [_make_edge(edge_type="BLOCKS", weight=2.0)]
        nodes = [_make_node()]
        result = quantify_impact(_make_traversal(affected=nodes, edges=edges, hops=1))
        assert result.dimensions["schedule"].confidence_score == pytest.approx(0.8)


# ──────────────────────────────────────────────────────────────────────────────
# quantify_impact — specialised dimensions
# ──────────────────────────────────────────────────────────────────────────────

class TestSpecialisedDimensions:
    def test_quality_counts_evidence_nodes(self):
        nodes = [_make_node("evidence"), _make_node("activity")]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["quality"].value == pytest.approx(1.0)

    def test_quality_counts_inspection_nodes(self):
        nodes = [_make_node("inspection"), _make_node("drawing")]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["quality"].value == pytest.approx(1.0)

    def test_safety_counts_inspection_and_commissioning(self):
        nodes = [_make_node("inspection"), _make_node("commissioning_item"), _make_node("activity")]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["safety"].value == pytest.approx(2.0)

    def test_regulatory_counts_gate_document_drawing(self):
        nodes = [_make_node("gate"), _make_node("document"), _make_node("drawing")]
        result = quantify_impact(_make_traversal(affected=nodes, hops=1))
        assert result.dimensions["regulatory"].value == pytest.approx(3.0)

    def test_affected_entity_count_matches_node_count(self):
        nodes = [_make_node() for _ in range(6)]
        result = quantify_impact(_make_traversal(affected=nodes, hops=2))
        assert result.affected_entity_count == 6


# ──────────────────────────────────────────────────────────────────────────────
# quantify_impact — impact_graph_edges
# ──────────────────────────────────────────────────────────────────────────────

class TestImpactGraphEdges:
    def test_edge_dict_contains_edge_type(self):
        sid, tid = uuid.uuid4(), uuid.uuid4()
        edges = [_make_edge(sid, tid, edge_type="BLOCKS", weight=2.0)]
        nodes = [_make_node()]
        result = quantify_impact(_make_traversal(affected=nodes, edges=edges, hops=1))
        assert result.impact_graph_edges[0]["edge_type"] == "BLOCKS"

    def test_edge_dict_contains_source_and_target(self):
        sid, tid = uuid.uuid4(), uuid.uuid4()
        edges = [_make_edge(sid, tid)]
        nodes = [_make_node()]
        result = quantify_impact(_make_traversal(affected=nodes, edges=edges, hops=1))
        ed = result.impact_graph_edges[0]
        assert "source_node_id" in ed
        assert "target_node_id" in ed

    def test_edge_dict_contains_weight(self):
        edges = [_make_edge(weight=0.75)]
        nodes = [_make_node()]
        result = quantify_impact(_make_traversal(affected=nodes, edges=edges, hops=1))
        assert result.impact_graph_edges[0]["weight"] == pytest.approx(0.75)


# ──────────────────────────────────────────────────────────────────────────────
# _generate_narrative
# ──────────────────────────────────────────────────────────────────────────────

class TestGenerateNarrative:
    def _dims(self, **overrides):
        dims = {d: ImpactDimension(d, 0.0, "unit", 0.0) for d in _IMPACT_DIMENSIONS}
        for k, v in overrides.items():
            dims[k] = ImpactDimension(k, v, "unit", 0.8)
        return dims

    def test_narrative_mentions_no_impact_when_count_zero(self):
        narrative = _generate_narrative(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_count=0,
            hops=0,
            dimensions=self._dims(),
        )
        assert "no cascading impact" in narrative

    def test_narrative_mentions_affected_count_when_nonzero(self):
        narrative = _generate_narrative(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_count=5,
            hops=2,
            dimensions=self._dims(),
        )
        assert "5" in narrative

    def test_narrative_mentions_schedule_when_nonzero(self):
        narrative = _generate_narrative(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_count=3,
            hops=1,
            dimensions=self._dims(schedule=4.0),
        )
        assert "Schedule impact" in narrative

    def test_narrative_mentions_safety_when_nonzero(self):
        narrative = _generate_narrative(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_count=2,
            hops=1,
            dimensions=self._dims(safety=1.0),
        )
        assert "Safety-critical" in narrative

    def test_narrative_mentions_regulatory_when_nonzero(self):
        narrative = _generate_narrative(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_count=2,
            hops=1,
            dimensions=self._dims(regulatory=2.0),
        )
        assert "Regulatory" in narrative

    def test_narrative_is_nonempty_string(self):
        narrative = _generate_narrative(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_count=0,
            hops=0,
            dimensions=self._dims(),
        )
        assert isinstance(narrative, str)
        assert len(narrative) > 0
