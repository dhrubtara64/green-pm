"""Unit tests for PIG edge writer — S4-03."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.pig.edge_writer as _ew
from app.pig.edge_writer import (
    _build_evidence_attributes,
    sync_evidence_node,
    write_evidence_pig_edges,
)

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_EVIDENCE_ID = uuid.uuid4()
_ENTITY_ID = uuid.uuid4()


def _make_evidence(**kwargs):
    defaults = dict(
        id=_EVIDENCE_ID,
        project_id=_PROJECT,
        tenant_id=_TENANT,
        entity_type="activity",
        entity_id=_ENTITY_ID,
        capture_type="site_photo",
        status="approved",
        reliability_tier="secondary",
        evidence_metadata={},
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_node(entity_type="evidence", entity_id=None):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.entity_type = entity_type
    m.entity_id = entity_id or uuid.uuid4()
    return m


def _make_session(source_node=None, target_node=None):
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    call_count = [0]
    async def scalar_side_effect(stmt):
        c = call_count[0]
        call_count[0] += 1
        return [source_node, target_node][min(c, 1)]

    session.scalar = scalar_side_effect
    return session


# ──────────────────────────────────────────────────────────────────────────────
# _build_evidence_attributes
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildEvidenceAttributes:
    def test_contains_capture_type(self):
        ev = _make_evidence(capture_type="drone_image")
        attrs = _build_evidence_attributes(ev)
        assert attrs["capture_type"] == "drone_image"

    def test_contains_status(self):
        ev = _make_evidence(status="approved")
        attrs = _build_evidence_attributes(ev)
        assert attrs["status"] == "approved"

    def test_contains_entity_type(self):
        ev = _make_evidence(entity_type="milestone")
        attrs = _build_evidence_attributes(ev)
        assert attrs["entity_type"] == "milestone"

    def test_contains_reliability_tier(self):
        ev = _make_evidence(reliability_tier="primary")
        attrs = _build_evidence_attributes(ev)
        assert attrs["reliability_tier"] == "primary"


# ──────────────────────────────────────────────────────────────────────────────
# sync_evidence_node
# ──────────────────────────────────────────────────────────────────────────────

class TestSyncEvidenceNode:
    @pytest.mark.asyncio
    async def test_calls_sync_entity(self):
        session = AsyncMock()
        ev = _make_evidence()
        mock_sync = AsyncMock(return_value=MagicMock())
        with patch.object(_ew, "sync_entity", mock_sync):
            await sync_evidence_node(session, ev)
        mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_entity_type_evidence(self):
        session = AsyncMock()
        ev = _make_evidence()
        mock_sync = AsyncMock(return_value=MagicMock())
        with patch.object(_ew, "sync_entity", mock_sync):
            await sync_evidence_node(session, ev)
        kwargs = mock_sync.call_args.kwargs
        assert kwargs["entity_type"] == "evidence"

    @pytest.mark.asyncio
    async def test_passes_evidence_id(self):
        session = AsyncMock()
        ev = _make_evidence()
        mock_sync = AsyncMock(return_value=MagicMock())
        with patch.object(_ew, "sync_entity", mock_sync):
            await sync_evidence_node(session, ev)
        kwargs = mock_sync.call_args.kwargs
        assert kwargs["entity_id"] == ev.id


# ──────────────────────────────────────────────────────────────────────────────
# write_evidence_pig_edges
# ──────────────────────────────────────────────────────────────────────────────

class TestWriteEvidencePigEdges:
    @pytest.mark.asyncio
    async def test_returns_empty_when_source_node_missing(self):
        ev = _make_evidence()
        session = _make_session(source_node=None, target_node=_make_node())
        edges = await write_evidence_pig_edges(session, ev, 0.75)
        assert edges == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_target_node_missing(self):
        ev = _make_evidence()
        session = _make_session(source_node=_make_node(), target_node=None)
        edges = await write_evidence_pig_edges(session, ev, 0.75)
        assert edges == []

    @pytest.mark.asyncio
    async def test_creates_two_edges_when_nodes_exist(self):
        ev = _make_evidence()
        source = _make_node("evidence", ev.id)
        target = _make_node("activity", ev.entity_id)
        session = _make_session(source_node=source, target_node=target)
        edges = await write_evidence_pig_edges(session, ev, 0.75)
        assert len(edges) == 2

    @pytest.mark.asyncio
    async def test_verifies_edge_has_score_as_weight(self):
        ev = _make_evidence()
        source = _make_node("evidence", ev.id)
        target = _make_node("activity", ev.entity_id)
        session = _make_session(source_node=source, target_node=target)
        session.add = MagicMock()
        added = []
        session.add.side_effect = lambda obj: added.append(obj)
        edges = await write_evidence_pig_edges(session, ev, 0.85)
        verifies = [e for e in added if e.edge_type == "VERIFIES"]
        assert len(verifies) == 1
        assert float(verifies[0].weight) == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_references_edge_has_weight_one(self):
        ev = _make_evidence()
        source = _make_node("evidence", ev.id)
        target = _make_node("activity", ev.entity_id)
        session = _make_session(source_node=source, target_node=target)
        session.add = MagicMock()
        added = []
        session.add.side_effect = lambda obj: added.append(obj)
        await write_evidence_pig_edges(session, ev, 0.5)
        references = [e for e in added if e.edge_type == "REFERENCES"]
        assert len(references) == 1
        assert float(references[0].weight) == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_flush_called_after_edges(self):
        ev = _make_evidence()
        source = _make_node()
        target = _make_node()
        session = _make_session(source_node=source, target_node=target)
        await write_evidence_pig_edges(session, ev, 0.5)
        assert session.flush.called
