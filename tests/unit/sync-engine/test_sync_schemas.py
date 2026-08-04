"""Tests for Synchronization & Consistency Engine schemas — S15-06."""
import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.sync.schemas import (
    INCONSISTENCY_THRESHOLD,
    ConsistencyReportResponse,
    InconsistencyResponse,
    InconsistencyResult,
    SyncCheckCreate,
    SyncEdge,
)


class TestInconsistencyThreshold:
    def test_is_float(self):
        assert isinstance(INCONSISTENCY_THRESHOLD, float)

    def test_value_is_0_2(self):
        assert INCONSISTENCY_THRESHOLD == pytest.approx(0.2)


class TestInconsistencyResult:
    def _make(self, **kw) -> InconsistencyResult:
        base = dict(
            entity_a_id=uuid.uuid4(),
            entity_b_id=uuid.uuid4(),
            edge_type="dependency",
            weight_a=0.2,
            weight_b=0.8,
            delta=0.6,
            recommendation="Reconcile weights",
        )
        return InconsistencyResult(**{**base, **kw})

    def test_stores_entity_a_id(self):
        a = uuid.uuid4()
        assert self._make(entity_a_id=a).entity_a_id == a

    def test_stores_entity_b_id(self):
        b = uuid.uuid4()
        assert self._make(entity_b_id=b).entity_b_id == b

    def test_stores_edge_type(self):
        assert self._make(edge_type="impact").edge_type == "impact"

    def test_stores_weight_a(self):
        assert self._make(weight_a=0.3).weight_a == pytest.approx(0.3)

    def test_stores_weight_b(self):
        assert self._make(weight_b=0.9).weight_b == pytest.approx(0.9)

    def test_stores_delta(self):
        assert self._make(delta=0.6).delta == pytest.approx(0.6)

    def test_stores_recommendation(self):
        r = "Review edge weight."
        assert self._make(recommendation=r).recommendation == r

    def test_is_frozen(self):
        result = self._make()
        with pytest.raises(FrozenInstanceError):
            result.delta = 999.0  # type: ignore[misc]


class TestSyncEdge:
    def test_stores_entity_a_id(self):
        a = uuid.uuid4()
        e = SyncEdge(entity_a_id=a, entity_b_id=uuid.uuid4(), edge_type="dep", weight=0.5)
        assert e.entity_a_id == a

    def test_stores_weight(self):
        e = SyncEdge(entity_a_id=uuid.uuid4(), entity_b_id=uuid.uuid4(), edge_type="dep", weight=0.75)
        assert e.weight == pytest.approx(0.75)

    def test_source_defaults_none(self):
        e = SyncEdge(entity_a_id=uuid.uuid4(), entity_b_id=uuid.uuid4(), edge_type="dep", weight=0.5)
        assert e.source is None

    def test_empty_edge_type_raises(self):
        with pytest.raises(ValidationError):
            SyncEdge(entity_a_id=uuid.uuid4(), entity_b_id=uuid.uuid4(), edge_type="", weight=0.5)


class TestSyncCheckCreate:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        c = SyncCheckCreate(project_id=pid, edges=[])
        assert c.project_id == pid

    def test_empty_edges_valid(self):
        c = SyncCheckCreate(project_id=uuid.uuid4(), edges=[])
        assert c.edges == []

    def test_stores_edges(self):
        edge = SyncEdge(
            entity_a_id=uuid.uuid4(), entity_b_id=uuid.uuid4(), edge_type="dep", weight=0.5
        )
        c = SyncCheckCreate(project_id=uuid.uuid4(), edges=[edge])
        assert len(c.edges) == 1


class TestInconsistencyResponse:
    def test_from_attributes_enabled(self):
        assert InconsistencyResponse.model_config.get("from_attributes") is True

    def test_stores_required_fields(self):
        r = InconsistencyResponse(
            id=uuid.uuid4(),
            entity_a_id=uuid.uuid4(),
            entity_b_id=uuid.uuid4(),
            edge_type="dep",
            weight_a=0.2,
            weight_b=0.8,
            delta=0.6,
            recommendation="Review weights",
        )
        assert r.edge_type == "dep"
        assert r.delta == pytest.approx(0.6)

    def test_optional_timestamps_default_none(self):
        r = InconsistencyResponse(
            id=uuid.uuid4(),
            entity_a_id=uuid.uuid4(),
            entity_b_id=uuid.uuid4(),
            edge_type="dep",
            weight_a=0.1,
            weight_b=0.9,
            delta=0.8,
            recommendation="x",
        )
        assert r.flagged_at is None
        assert r.resolved_at is None


class TestConsistencyReportResponse:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        r = ConsistencyReportResponse(
            project_id=pid, total_edges_checked=5, inconsistencies_found=0, inconsistencies=[]
        )
        assert r.project_id == pid

    def test_stores_counts(self):
        r = ConsistencyReportResponse(
            project_id=uuid.uuid4(),
            total_edges_checked=10,
            inconsistencies_found=3,
            inconsistencies=[],
        )
        assert r.total_edges_checked == 10
        assert r.inconsistencies_found == 3

    def test_empty_inconsistencies_valid(self):
        r = ConsistencyReportResponse(
            project_id=uuid.uuid4(), total_edges_checked=0, inconsistencies_found=0,
            inconsistencies=[]
        )
        assert r.inconsistencies == []
