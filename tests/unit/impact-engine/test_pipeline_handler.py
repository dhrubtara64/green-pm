"""Unit tests for change.initiated pipeline handler — S5-03."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.pipeline.handler as _handler
from app.pipeline.handler import (
    InvalidChangePayloadError,
    handle_change_initiated,
    parse_change_initiated_payload,
)
from app.traversal.pig_traversal import TraversalResult
from app.impact.schemas import ImpactDimension, ImpactResult, _IMPACT_DIMENSIONS

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_ENTITY_ID = uuid.uuid4()
_CHANGE_ID = uuid.uuid4()


def _make_valid_payload(**kwargs) -> dict:
    payload = {
        "change_id": str(_CHANGE_ID),
        "project_id": str(_PROJECT),
        "entity_type": "activity",
        "entity_id": str(_ENTITY_ID),
    }
    payload.update(kwargs)
    return payload


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_change_mock(change_id=None):
    m = MagicMock()
    m.id = change_id or _CHANGE_ID
    m.status = "initiated"
    m.project_id = _PROJECT
    m.entity_type = "activity"
    m.entity_id = _ENTITY_ID
    return m


def _make_traversal() -> TraversalResult:
    return TraversalResult(
        start_entity_type="activity",
        start_entity_id=_ENTITY_ID,
        affected_nodes=(),
        edges_traversed=(),
        hops_reached=0,
    )


def _make_impact() -> ImpactResult:
    dims = {d: ImpactDimension(d, 0.0, "unit", 0.0) for d in _IMPACT_DIMENSIONS}
    return ImpactResult(
        dimensions=dims,
        affected_entity_count=0,
        impact_graph_edges=(),
        narrative_summary="No impact.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# parse_change_initiated_payload
# ──────────────────────────────────────────────────────────────────────────────

class TestParseChangeInitiatedPayload:
    def test_returns_parsed_dict_on_valid_payload(self):
        result = parse_change_initiated_payload(_make_valid_payload())
        assert isinstance(result["change_id"], uuid.UUID)
        assert isinstance(result["project_id"], uuid.UUID)
        assert result["entity_type"] == "activity"
        assert isinstance(result["entity_id"], uuid.UUID)

    def test_raises_on_missing_change_id(self):
        payload = _make_valid_payload()
        del payload["change_id"]
        with pytest.raises(InvalidChangePayloadError, match="change_id"):
            parse_change_initiated_payload(payload)

    def test_raises_on_missing_project_id(self):
        payload = _make_valid_payload()
        del payload["project_id"]
        with pytest.raises(InvalidChangePayloadError, match="project_id"):
            parse_change_initiated_payload(payload)

    def test_raises_on_missing_entity_type(self):
        payload = _make_valid_payload()
        del payload["entity_type"]
        with pytest.raises(InvalidChangePayloadError, match="entity_type"):
            parse_change_initiated_payload(payload)

    def test_raises_on_missing_entity_id(self):
        payload = _make_valid_payload()
        del payload["entity_id"]
        with pytest.raises(InvalidChangePayloadError, match="entity_id"):
            parse_change_initiated_payload(payload)

    def test_raises_on_empty_payload(self):
        with pytest.raises(InvalidChangePayloadError):
            parse_change_initiated_payload({})


# ──────────────────────────────────────────────────────────────────────────────
# handle_change_initiated
# ──────────────────────────────────────────────────────────────────────────────

class TestHandleChangeInitiated:
    def _patches(self, change=None, traversal=None, impact=None):
        change = change or _make_change_mock()
        traversal = traversal or _make_traversal()
        impact = impact or _make_impact()
        return (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=change)),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=traversal)),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=impact)),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        )

    @pytest.mark.asyncio
    async def test_sets_change_status_to_assessing(self):
        session = _make_session()
        change = _make_change_mock()
        status_states = []
        orig_flush = session.flush

        async def capture_flush():
            status_states.append(change.status)

        session.flush = capture_flush
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=change)),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            await handle_change_initiated(session, _TENANT, _make_valid_payload())
        assert "assessing" in status_states

    @pytest.mark.asyncio
    async def test_calls_traverse_impact(self):
        session = _make_session()
        mock_traverse = AsyncMock(return_value=_make_traversal())
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=mock_traverse),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            await handle_change_initiated(session, _TENANT, _make_valid_payload())
        mock_traverse.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_quantify_impact(self):
        session = _make_session()
        mock_quantify = MagicMock(return_value=_make_impact())
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=mock_quantify),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            await handle_change_initiated(session, _TENANT, _make_valid_payload())
        mock_quantify.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_impact_assessment(self):
        session = _make_session()
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            assessment = await handle_change_initiated(session, _TENANT, _make_valid_payload())
        assert session.add.called
        assert assessment.status == "assessed"

    @pytest.mark.asyncio
    async def test_sets_change_status_to_assessed(self):
        session = _make_session()
        change = _make_change_mock()
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=change)),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            await handle_change_initiated(session, _TENANT, _make_valid_payload())
        assert change.status == "assessed"

    @pytest.mark.asyncio
    async def test_emits_impact_assessed_outbox_event(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=mock_outbox),
        ):
            await handle_change_initiated(session, _TENANT, _make_valid_payload())
        mock_outbox.assert_called_once()
        assert mock_outbox.call_args.kwargs["event_type"] == "ImpactAssessed"

    @pytest.mark.asyncio
    async def test_outbox_topic_is_greenpm_impact(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=mock_outbox),
        ):
            await handle_change_initiated(session, _TENANT, _make_valid_payload())
        assert mock_outbox.call_args.kwargs["topic"] == "greenpm.impact"

    @pytest.mark.asyncio
    async def test_assessment_computed_at_is_set(self):
        session = _make_session()
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            assessment = await handle_change_initiated(session, _TENANT, _make_valid_payload())
        assert assessment.computed_at is not None

    @pytest.mark.asyncio
    async def test_assessment_narrative_populated(self):
        session = _make_session()
        with (
            patch.object(_handler, "get_change", new=AsyncMock(return_value=_make_change_mock())),
            patch.object(_handler, "traverse_impact", new=AsyncMock(return_value=_make_traversal())),
            patch.object(_handler, "quantify_impact", new=MagicMock(return_value=_make_impact())),
            patch.object(_handler, "write_outbox_event", new=AsyncMock()),
        ):
            assessment = await handle_change_initiated(session, _TENANT, _make_valid_payload())
        assert assessment.narrative_summary == "No impact."
