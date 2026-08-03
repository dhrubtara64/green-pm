"""Unit tests for CPM service — S6-01, S6-04, S6-06."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cpm.service import (
    CPMNotFoundError,
    _fetch_cpm_data,
    get_activity_float_info,
    get_latest_cpm_result,
    run_cpm_for_project,
)
from app.cpm.schemas import _DEPENDENCY_TYPES


_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()


def _make_graph_node(entity_type="activity", duration=5.0):
    n = MagicMock()
    n.id = uuid.uuid4()
    n.entity_id = uuid.uuid4()
    n.entity_type = entity_type
    n.attributes = {"duration_days": duration}
    n.tenant_id = _TENANT
    n.project_id = _PROJECT
    return n


def _make_graph_edge(src_node, tgt_node, dep_type="FS", lag=0.0):
    e = MagicMock()
    e.source_node_id = src_node.id
    e.target_node_id = tgt_node.id
    e.edge_type = "BLOCKS"
    e.edge_attributes = {"dep_type": dep_type}
    e.weight = lag
    e.tenant_id = _TENANT
    e.project_id = _PROJECT
    return e


def _make_session(nodes=(), edges=()):
    session = AsyncMock()

    async def execute_side_effect(query):
        result = MagicMock()
        result.scalars.return_value.all.return_value = list(
            nodes if "GraphNode" in str(query) or not edges else edges
        )
        return result

    # Cycle through nodes then edges
    call_count = [0]
    async def execute_side(query):
        r = MagicMock()
        if call_count[0] == 0:
            r.scalars.return_value.all.return_value = list(nodes)
        else:
            r.scalars.return_value.all.return_value = list(edges)
        call_count[0] += 1
        return r

    session.execute = AsyncMock(side_effect=execute_side)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    return session


# ──────────────────────────────────────────────────────────────────────────────
# _fetch_cpm_data
# ──────────────────────────────────────────────────────────────────────────────

class TestFetchCPMData:
    @pytest.mark.asyncio
    async def test_no_nodes_returns_empty(self):
        session = _make_session(nodes=[])
        nodes, edges = await _fetch_cpm_data(session, _TENANT, _PROJECT)
        assert nodes == []
        assert edges == []

    @pytest.mark.asyncio
    async def test_nodes_returned_as_cpm_nodes(self):
        n1 = _make_graph_node(duration=3.0)
        session = _make_session(nodes=[n1])
        nodes, _ = await _fetch_cpm_data(session, _TENANT, _PROJECT)
        assert len(nodes) == 1
        assert nodes[0].duration == pytest.approx(3.0)

    @pytest.mark.asyncio
    async def test_missing_duration_defaults_to_zero(self):
        n1 = _make_graph_node()
        n1.attributes = {}
        session = _make_session(nodes=[n1])
        nodes, _ = await _fetch_cpm_data(session, _TENANT, _PROJECT)
        assert nodes[0].duration == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_edges_returned_with_dep_type(self):
        n1, n2 = _make_graph_node(duration=3.0), _make_graph_node(duration=2.0)
        e1 = _make_graph_edge(n1, n2, dep_type="SS")
        session = _make_session(nodes=[n1, n2], edges=[e1])
        _, edges = await _fetch_cpm_data(session, _TENANT, _PROJECT)
        assert len(edges) == 1
        assert edges[0].dep_type == "SS"

    @pytest.mark.asyncio
    async def test_invalid_dep_type_defaults_to_fs(self):
        n1, n2 = _make_graph_node(duration=2.0), _make_graph_node(duration=2.0)
        e1 = _make_graph_edge(n1, n2)
        e1.edge_attributes = {"dep_type": "INVALID"}
        session = _make_session(nodes=[n1, n2], edges=[e1])
        _, edges = await _fetch_cpm_data(session, _TENANT, _PROJECT)
        assert edges[0].dep_type == "FS"


# ──────────────────────────────────────────────────────────────────────────────
# run_cpm_for_project
# ──────────────────────────────────────────────────────────────────────────────

class TestRunCPMForProject:
    @pytest.mark.asyncio
    async def test_result_added_to_session(self):
        n1, n2 = _make_graph_node(duration=3.0), _make_graph_node(duration=2.0)
        e1 = _make_graph_edge(n1, n2)
        session = _make_session(nodes=[n1, n2], edges=[e1])
        await run_cpm_for_project(session, _TENANT, _PROJECT)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called_after_add(self):
        n1 = _make_graph_node(duration=5.0)
        session = _make_session(nodes=[n1])
        await run_cpm_for_project(session, _TENANT, _PROJECT)
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_result_status_is_computed(self):
        n1 = _make_graph_node(duration=5.0)
        session = _make_session(nodes=[n1])
        result = await run_cpm_for_project(session, _TENANT, _PROJECT)
        assert result.status == "computed"

    @pytest.mark.asyncio
    async def test_result_project_id_matches(self):
        n1 = _make_graph_node(duration=5.0)
        session = _make_session(nodes=[n1])
        result = await run_cpm_for_project(session, _TENANT, _PROJECT)
        assert result.project_id == _PROJECT

    @pytest.mark.asyncio
    async def test_result_has_uuid_id(self):
        n1 = _make_graph_node(duration=5.0)
        session = _make_session(nodes=[n1])
        result = await run_cpm_for_project(session, _TENANT, _PROJECT)
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_computed_at_is_set(self):
        n1 = _make_graph_node(duration=5.0)
        session = _make_session(nodes=[n1])
        result = await run_cpm_for_project(session, _TENANT, _PROJECT)
        assert result.computed_at is not None

    @pytest.mark.asyncio
    async def test_activity_floats_dict_populated(self):
        n1 = _make_graph_node(duration=5.0)
        session = _make_session(nodes=[n1])
        result = await run_cpm_for_project(session, _TENANT, _PROJECT)
        assert isinstance(result.activity_floats, dict)
        assert len(result.activity_floats) == 1


# ──────────────────────────────────────────────────────────────────────────────
# get_latest_cpm_result
# ──────────────────────────────────────────────────────────────────────────────

class TestGetLatestCPMResult:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_result(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        result = await get_latest_cpm_result(session, _TENANT, _PROJECT)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_record_when_exists(self):
        mock_record = MagicMock()
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=mock_record)
        result = await get_latest_cpm_result(session, _TENANT, _PROJECT)
        assert result is mock_record


# ──────────────────────────────────────────────────────────────────────────────
# get_activity_float_info
# ──────────────────────────────────────────────────────────────────────────────

class TestGetActivityFloatInfo:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_cpm_result(self):
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        result = await get_activity_float_info(session, _TENANT, _PROJECT, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_float_info_for_known_activity(self):
        aid = uuid.uuid4()
        mock_record = MagicMock()
        mock_record.activity_floats = {
            str(aid): {"total_float": 0.0, "is_critical": True}
        }
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=mock_record)
        result = await get_activity_float_info(session, _TENANT, _PROJECT, aid)
        assert result is not None
        assert result["total_float"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_activity(self):
        mock_record = MagicMock()
        mock_record.activity_floats = {}
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=mock_record)
        result = await get_activity_float_info(session, _TENANT, _PROJECT, uuid.uuid4())
        assert result is None
