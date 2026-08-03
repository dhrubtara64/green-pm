"""Unit tests for PIG BFS traversal — S5-01."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.traversal.pig_traversal as _trav
from app.traversal.pig_traversal import (
    TraversalResult,
    _CASCADE_EDGE_TYPES,
    clear_cache,
    traverse_impact,
)

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_ENTITY_ID = uuid.uuid4()


def _make_node(entity_type="activity", entity_id=None, node_id=None):
    m = MagicMock()
    m.id = node_id or uuid.uuid4()
    m.entity_type = entity_type
    m.entity_id = entity_id or uuid.uuid4()
    return m


def _make_edge(source_id, target_id, edge_type="BLOCKS", weight=1.0):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.source_node_id = source_id
    m.target_node_id = target_id
    m.edge_type = edge_type
    m.weight = weight
    return m


def _make_session():
    return AsyncMock()


def _mock_no_outgoing(session):
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)


@pytest.fixture(autouse=True)
def _clear_traversal_cache():
    clear_cache()
    yield
    clear_cache()


# ──────────────────────────────────────────────────────────────────────────────
# TraversalResult dataclass
# ──────────────────────────────────────────────────────────────────────────────

class TestTraversalResult:
    def test_is_frozen(self):
        r = TraversalResult(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_nodes=(),
            edges_traversed=(),
            hops_reached=0,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.hops_reached = 5  # type: ignore[misc]

    def test_affected_entity_ids_returns_list(self):
        node = _make_node(entity_id=_ENTITY_ID)
        r = TraversalResult(
            start_entity_type="activity",
            start_entity_id=_ENTITY_ID,
            affected_nodes=(node,),
            edges_traversed=(),
            hops_reached=1,
        )
        ids = r.affected_entity_ids
        assert isinstance(ids, list)
        assert ids[0] == _ENTITY_ID

    def test_affected_nodes_is_tuple(self):
        r = TraversalResult("activity", _ENTITY_ID, (), (), 0)
        assert isinstance(r.affected_nodes, tuple)

    def test_edges_traversed_is_tuple(self):
        r = TraversalResult("activity", _ENTITY_ID, (), (), 0)
        assert isinstance(r.edges_traversed, tuple)


# ──────────────────────────────────────────────────────────────────────────────
# Cascade edge types
# ──────────────────────────────────────────────────────────────────────────────

class TestCascadeEdgeTypes:
    @pytest.mark.parametrize("et", ["BLOCKS", "IMPACTS", "TRIGGERS", "DEPENDS_ON"])
    def test_cascade_types_present(self, et: str):
        assert et in _CASCADE_EDGE_TYPES

    def test_non_cascade_type_not_in_set(self):
        assert "OWNS" not in _CASCADE_EDGE_TYPES
        assert "REFERENCES" not in _CASCADE_EDGE_TYPES


# ──────────────────────────────────────────────────────────────────────────────
# traverse_impact — start node missing
# ──────────────────────────────────────────────────────────────────────────────

class TestTraverseImpactStartMissing:
    @pytest.mark.asyncio
    async def test_returns_empty_when_start_node_not_found(self):
        session = _make_session()
        with patch.object(_trav, "_find_node", new=AsyncMock(return_value=None)):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert result.affected_nodes == ()
        assert result.edges_traversed == ()
        assert result.hops_reached == 0

    @pytest.mark.asyncio
    async def test_hops_reached_is_zero_when_no_affected(self):
        session = _make_session()
        start = _make_node()
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(return_value=[])),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert result.hops_reached == 0
        assert result.affected_nodes == ()


# ──────────────────────────────────────────────────────────────────────────────
# traverse_impact — BFS traversal
# ──────────────────────────────────────────────────────────────────────────────

class TestTraverseImpactBFS:
    @pytest.mark.asyncio
    async def test_returns_directly_impacted_node_via_blocks(self):
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        target = _make_node(node_id=uuid.uuid4())
        edge = _make_edge(start.id, target.id, edge_type="BLOCKS")
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(side_effect=[
                [edge],  # start node outgoing
                [],      # target node outgoing
            ])),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(return_value=target)),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert len(result.affected_nodes) == 1
        assert result.affected_nodes[0] is target

    @pytest.mark.asyncio
    async def test_returns_impacted_node_via_impacts_edge(self):
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        target = _make_node(node_id=uuid.uuid4())
        edge = _make_edge(start.id, target.id, edge_type="IMPACTS")
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(side_effect=[
                [edge], [],
            ])),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(return_value=target)),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert len(result.affected_nodes) == 1

    @pytest.mark.asyncio
    async def test_respects_max_hops_1(self):
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        hop1 = _make_node(node_id=uuid.uuid4())
        hop2 = _make_node(node_id=uuid.uuid4())
        edge1 = _make_edge(start.id, hop1.id)
        edge2 = _make_edge(hop1.id, hop2.id)
        # With max_hops=1, hop2 should not be reached
        find_outgoing_calls = [
            [edge1],  # start → hop1
            [edge2],  # hop1 → hop2 (won't process since depth == max_hops)
        ]
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(side_effect=find_outgoing_calls)),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(side_effect=[hop1, hop2])),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
                max_hops=1,
            )
        assert len(result.affected_nodes) == 1
        assert result.affected_nodes[0] is hop1

    @pytest.mark.asyncio
    async def test_handles_cycles_via_visited_set(self):
        """A→B→A cycle should not cause infinite loop."""
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        node_b = _make_node(node_id=uuid.uuid4())
        edge_ab = _make_edge(start.id, node_b.id)
        edge_ba = _make_edge(node_b.id, start.id)  # cycle back
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(side_effect=[
                [edge_ab],   # start outgoing
                [edge_ba],   # node_b outgoing → points back to start (visited)
            ])),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(side_effect=[
                node_b,  # target of edge_ab
                start,   # target of edge_ba — already visited, skipped
            ])),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
                max_hops=5,
            )
        assert len(result.affected_nodes) == 1

    @pytest.mark.asyncio
    async def test_hops_reached_equals_actual_depth(self):
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        hop1 = _make_node(node_id=uuid.uuid4())
        hop2 = _make_node(node_id=uuid.uuid4())
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(side_effect=[
                [_make_edge(start.id, hop1.id)],
                [_make_edge(hop1.id, hop2.id)],
                [],
            ])),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(side_effect=[hop1, hop2])),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
                max_hops=5,
            )
        assert result.hops_reached == 2

    @pytest.mark.asyncio
    async def test_start_entity_not_in_affected_nodes(self):
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        target = _make_node(node_id=uuid.uuid4())
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(side_effect=[[_make_edge(start.id, target.id)], []])),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(return_value=target)),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        node_ids = [n.id for n in result.affected_nodes]
        assert start.id not in node_ids

    @pytest.mark.asyncio
    async def test_missing_target_node_skipped(self):
        """If _find_node_by_id returns None for a target, skip it gracefully."""
        session = _make_session()
        start = _make_node(node_id=uuid.uuid4())
        edge = _make_edge(start.id, uuid.uuid4())
        with (
            patch.object(_trav, "_find_node", new=AsyncMock(return_value=start)),
            patch.object(_trav, "_find_outgoing_edges", new=AsyncMock(return_value=[edge])),
            patch.object(_trav, "_find_node_by_id", new=AsyncMock(return_value=None)),
        ):
            result = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert result.affected_nodes == ()


# ──────────────────────────────────────────────────────────────────────────────
# traverse_impact — caching
# ──────────────────────────────────────────────────────────────────────────────

class TestTraversalCache:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_db_on_second_call(self):
        session = _make_session()
        mock_find = AsyncMock(return_value=None)
        with patch.object(_trav, "_find_node", new=mock_find):
            await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
            await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert mock_find.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_returns_same_result(self):
        session = _make_session()
        with patch.object(_trav, "_find_node", new=AsyncMock(return_value=None)):
            r1 = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
            r2 = await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_clear_cache_forces_new_db_call(self):
        session = _make_session()
        mock_find = AsyncMock(return_value=None)
        with patch.object(_trav, "_find_node", new=mock_find):
            await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
            clear_cache()
            await traverse_impact(
                session, tenant_id=_TENANT, project_id=_PROJECT,
                start_entity_type="activity", start_entity_id=_ENTITY_ID,
            )
        assert mock_find.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_expired_after_ttl(self):
        import time as _time
        session = _make_session()
        mock_find = AsyncMock(return_value=None)
        with patch.object(_trav, "_find_node", new=mock_find):
            with patch.object(_trav.time, "monotonic", side_effect=[0.0, 61.0, 61.0]):
                await traverse_impact(
                    session, tenant_id=_TENANT, project_id=_PROJECT,
                    start_entity_type="activity", start_entity_id=_ENTITY_ID,
                )
                await traverse_impact(
                    session, tenant_id=_TENANT, project_id=_PROJECT,
                    start_entity_type="activity", start_entity_id=_ENTITY_ID,
                )
        assert mock_find.call_count == 2
