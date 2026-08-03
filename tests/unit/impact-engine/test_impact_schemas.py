"""Unit tests for Impact dimension schemas — S5-02."""
from __future__ import annotations

import uuid

import pytest

from app.impact.schemas import (
    ImpactDimension,
    ImpactResult,
    _IMPACT_DIMENSIONS,
)


def _make_dim(dimension="scope", value=5.0, unit="node_count", confidence=0.5) -> ImpactDimension:
    return ImpactDimension(dimension=dimension, value=value, unit=unit, confidence_score=confidence)


def _make_all_dims() -> dict[str, ImpactDimension]:
    return {
        d: _make_dim(dimension=d, value=0.0, unit="node_count", confidence=0.0)
        for d in _IMPACT_DIMENSIONS
    }


def _make_result(**kwargs) -> ImpactResult:
    defaults = {
        "dimensions": _make_all_dims(),
        "affected_entity_count": 0,
        "impact_graph_edges": (),
        "narrative_summary": "No impact.",
    }
    defaults.update(kwargs)
    return ImpactResult(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# _IMPACT_DIMENSIONS
# ──────────────────────────────────────────────────────────────────────────────

class TestImpactDimensionsConstant:
    def test_has_6_dimensions(self):
        assert len(_IMPACT_DIMENSIONS) == 6

    @pytest.mark.parametrize("dim", ["scope", "schedule", "cost", "quality", "safety", "regulatory"])
    def test_all_6_present(self, dim: str):
        assert dim in _IMPACT_DIMENSIONS


# ──────────────────────────────────────────────────────────────────────────────
# ImpactDimension
# ──────────────────────────────────────────────────────────────────────────────

class TestImpactDimension:
    def test_has_dimension_field(self):
        d = _make_dim(dimension="scope")
        assert d.dimension == "scope"

    def test_has_value_field(self):
        d = _make_dim(value=3.0)
        assert d.value == pytest.approx(3.0)

    def test_has_unit_field(self):
        d = _make_dim(unit="days")
        assert d.unit == "days"

    def test_has_confidence_score_field(self):
        d = _make_dim(confidence=0.8)
        assert d.confidence_score == pytest.approx(0.8)

    def test_is_frozen(self):
        d = _make_dim()
        with pytest.raises((AttributeError, TypeError)):
            d.value = 99.0  # type: ignore[misc]

    def test_zero_value_is_valid(self):
        d = _make_dim(value=0.0, confidence=0.0)
        assert d.value == 0.0
        assert d.confidence_score == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# ImpactResult
# ──────────────────────────────────────────────────────────────────────────────

class TestImpactResult:
    def test_has_dimensions(self):
        r = _make_result()
        assert isinstance(r.dimensions, dict)

    def test_has_affected_entity_count(self):
        r = _make_result(affected_entity_count=5)
        assert r.affected_entity_count == 5

    def test_has_impact_graph_edges(self):
        r = _make_result()
        assert isinstance(r.impact_graph_edges, tuple)

    def test_has_narrative_summary(self):
        r = _make_result(narrative_summary="Test summary.")
        assert r.narrative_summary == "Test summary."

    def test_is_frozen(self):
        r = _make_result()
        with pytest.raises((AttributeError, TypeError)):
            r.affected_entity_count = 99  # type: ignore[misc]

    def test_as_dict_contains_all_6_dimensions(self):
        r = _make_result()
        d = r.as_dict()
        for dim in _IMPACT_DIMENSIONS:
            assert dim in d["dimensions"]

    def test_as_dict_dimension_has_required_keys(self):
        r = _make_result()
        d = r.as_dict()
        for dim_data in d["dimensions"].values():
            assert "value" in dim_data
            assert "unit" in dim_data
            assert "confidence_score" in dim_data

    def test_as_dict_is_serializable(self):
        import json
        r = _make_result(affected_entity_count=2, narrative_summary="X")
        d = r.as_dict()
        # Should not raise
        json.dumps(d)

    def test_as_dict_affected_entity_count(self):
        r = _make_result(affected_entity_count=7)
        assert r.as_dict()["affected_entity_count"] == 7

    def test_as_dict_narrative(self):
        r = _make_result(narrative_summary="Important!")
        assert r.as_dict()["narrative_summary"] == "Important!"
