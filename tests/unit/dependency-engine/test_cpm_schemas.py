"""Unit tests for CPM domain schemas — S6-01, S6-02, S6-03."""
from __future__ import annotations

import uuid

import pytest

from app.cpm.schemas import (
    ActivityFloat,
    CPMEdge,
    CPMNode,
    CPMResult,
    _DEPENDENCY_TYPES,
    _NEAR_CRITICAL_THRESHOLD,
)


_A = uuid.uuid4()
_B = uuid.uuid4()
_NODE_A = uuid.uuid4()


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_dependency_types_contains_fs(self):
        assert "FS" in _DEPENDENCY_TYPES

    def test_dependency_types_contains_ss(self):
        assert "SS" in _DEPENDENCY_TYPES

    def test_dependency_types_contains_ff(self):
        assert "FF" in _DEPENDENCY_TYPES

    def test_dependency_types_contains_sf(self):
        assert "SF" in _DEPENDENCY_TYPES

    def test_near_critical_threshold_is_two_days(self):
        assert _NEAR_CRITICAL_THRESHOLD == pytest.approx(2.0)


# ──────────────────────────────────────────────────────────────────────────────
# CPMNode
# ──────────────────────────────────────────────────────────────────────────────

class TestCPMNode:
    def test_stores_entity_id(self):
        node = CPMNode(entity_id=_A, node_id=_NODE_A, duration=5.0)
        assert node.entity_id == _A

    def test_stores_node_id(self):
        node = CPMNode(entity_id=_A, node_id=_NODE_A, duration=5.0)
        assert node.node_id == _NODE_A

    def test_stores_duration(self):
        node = CPMNode(entity_id=_A, node_id=_NODE_A, duration=3.5)
        assert node.duration == pytest.approx(3.5)

    def test_frozen_rejects_mutation(self):
        node = CPMNode(entity_id=_A, node_id=_NODE_A, duration=5.0)
        with pytest.raises(Exception):
            node.duration = 10.0  # type: ignore[misc]

    def test_zero_duration_valid(self):
        node = CPMNode(entity_id=_A, node_id=_NODE_A, duration=0.0)
        assert node.duration == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# CPMEdge
# ──────────────────────────────────────────────────────────────────────────────

class TestCPMEdge:
    def test_stores_source_and_target(self):
        edge = CPMEdge(source_entity_id=_A, target_entity_id=_B, dep_type="FS")
        assert edge.source_entity_id == _A
        assert edge.target_entity_id == _B

    def test_stores_dep_type(self):
        edge = CPMEdge(source_entity_id=_A, target_entity_id=_B, dep_type="SS")
        assert edge.dep_type == "SS"

    def test_default_lag_is_zero(self):
        edge = CPMEdge(source_entity_id=_A, target_entity_id=_B, dep_type="FS")
        assert edge.lag == pytest.approx(0.0)

    def test_stores_positive_lag(self):
        edge = CPMEdge(source_entity_id=_A, target_entity_id=_B, dep_type="FS", lag=3.0)
        assert edge.lag == pytest.approx(3.0)

    def test_stores_negative_lag_lead(self):
        edge = CPMEdge(source_entity_id=_A, target_entity_id=_B, dep_type="FS", lag=-2.0)
        assert edge.lag == pytest.approx(-2.0)

    def test_frozen_rejects_mutation(self):
        edge = CPMEdge(source_entity_id=_A, target_entity_id=_B, dep_type="FS")
        with pytest.raises(Exception):
            edge.lag = 5.0  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# ActivityFloat
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityFloat:
    def _make(self, tf=0.0, ff=0.0, is_critical=True) -> ActivityFloat:
        return ActivityFloat(
            entity_id=_A,
            early_start=0.0,
            early_finish=5.0,
            late_start=0.0,
            late_finish=5.0,
            total_float=tf,
            free_float=ff,
            is_critical=is_critical,
        )

    def test_stores_entity_id(self):
        af = self._make()
        assert af.entity_id == _A

    def test_stores_total_float(self):
        af = self._make(tf=2.5)
        assert af.total_float == pytest.approx(2.5)

    def test_stores_is_critical_true(self):
        af = self._make(is_critical=True)
        assert af.is_critical is True

    def test_stores_is_critical_false(self):
        af = self._make(is_critical=False)
        assert af.is_critical is False

    def test_frozen_rejects_mutation(self):
        af = self._make()
        with pytest.raises(Exception):
            af.total_float = 99.0  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# CPMResult
# ──────────────────────────────────────────────────────────────────────────────

class TestCPMResult:
    def _af(self, eid=None) -> ActivityFloat:
        eid = eid or _A
        return ActivityFloat(
            entity_id=eid,
            early_start=0.0, early_finish=5.0,
            late_start=0.0, late_finish=5.0,
            total_float=0.0, free_float=0.0, is_critical=True,
        )

    def test_stores_project_duration(self):
        result = CPMResult(
            project_duration=10.0, critical_path=(_A,), near_critical=(), floats={_A: self._af()}
        )
        assert result.project_duration == pytest.approx(10.0)

    def test_as_dict_contains_project_duration(self):
        result = CPMResult(
            project_duration=5.0, critical_path=(_A,), near_critical=(), floats={_A: self._af()}
        )
        d = result.as_dict()
        assert d["project_duration"] == pytest.approx(5.0)

    def test_as_dict_critical_path_contains_str_uuids(self):
        result = CPMResult(
            project_duration=5.0, critical_path=(_A,), near_critical=(), floats={_A: self._af()}
        )
        d = result.as_dict()
        assert str(_A) in d["critical_path"]

    def test_as_dict_activity_floats_keyed_by_str_uuid(self):
        result = CPMResult(
            project_duration=5.0, critical_path=(_A,), near_critical=(), floats={_A: self._af()}
        )
        d = result.as_dict()
        assert str(_A) in d["activity_floats"]

    def test_as_dict_activity_float_entry_has_required_keys(self):
        result = CPMResult(
            project_duration=5.0, critical_path=(_A,), near_critical=(), floats={_A: self._af()}
        )
        entry = result.as_dict()["activity_floats"][str(_A)]
        for key in ("early_start", "early_finish", "late_start", "late_finish",
                    "total_float", "free_float", "is_critical"):
            assert key in entry

    def test_frozen_rejects_mutation(self):
        result = CPMResult(project_duration=5.0, critical_path=(), near_critical=(), floats={})
        with pytest.raises(Exception):
            result.project_duration = 99.0  # type: ignore[misc]
