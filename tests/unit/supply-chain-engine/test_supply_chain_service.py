"""Unit tests for dispatch service — S7-01, S7-02, S7-05."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dispatch.service import (
    DispatchNotFoundError,
    count_critical_materials,
    create_dispatch,
    get_dispatch,
    list_dispatches,
    transition_dispatch_stage,
)
from app.dispatch.schemas import _DISPATCH_STAGES
from app.dispatch.state_machine import InvalidTransitionError


_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_PO = uuid.uuid4()


def _make_session(scalar_value=None, scalars_value=None):
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=scalar_value)

    result = MagicMock()
    result.scalars.return_value.all.return_value = list(scalars_value or [])
    session.execute = AsyncMock(return_value=result)
    return session


def _make_dispatch(stage="PO_RAISED", score=0.0):
    d = MagicMock()
    d.id = uuid.uuid4()
    d.tenant_id = _TENANT
    d.project_id = _PROJECT
    d.po_id = _PO
    d.dispatch_number = "DISP-001"
    d.current_stage = stage
    d.material_readiness_score = score
    d.critical_material_count = 0
    return d


class TestCreateDispatch:
    @pytest.mark.asyncio
    async def test_session_add_called(self):
        session = _make_session()
        await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-001")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self):
        session = _make_session()
        await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-001")
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_dispatch_with_uuid(self):
        session = _make_session()
        result = await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-001")
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_initial_stage_is_po_raised(self):
        session = _make_session()
        result = await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-001")
        assert result.current_stage == "PO_RAISED"

    @pytest.mark.asyncio
    async def test_initial_score_is_zero(self):
        session = _make_session()
        result = await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-001")
        assert result.material_readiness_score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_dispatch_number_stored(self):
        session = _make_session()
        result = await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-XYZ")
        assert result.dispatch_number == "DISP-XYZ"

    @pytest.mark.asyncio
    async def test_project_id_stored(self):
        session = _make_session()
        result = await create_dispatch(session, _TENANT, _PO, _PROJECT, "DISP-001")
        assert result.project_id == _PROJECT


class TestGetDispatch:
    @pytest.mark.asyncio
    async def test_returns_dispatch_when_found(self):
        mock_dispatch = _make_dispatch()
        session = _make_session(scalar_value=mock_dispatch)
        result = await get_dispatch(session, _TENANT, mock_dispatch.id)
        assert result is mock_dispatch

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self):
        session = _make_session(scalar_value=None)
        with pytest.raises(DispatchNotFoundError):
            await get_dispatch(session, _TENANT, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_dispatch_id(self):
        session = _make_session(scalar_value=None)
        did = uuid.uuid4()
        with pytest.raises(DispatchNotFoundError, match=str(did)):
            await get_dispatch(session, _TENANT, did)


class TestListDispatches:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none(self):
        session = _make_session(scalars_value=[])
        result = await list_dispatches(session, _TENANT, _PROJECT)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_all_dispatches(self):
        d1, d2 = _make_dispatch(), _make_dispatch()
        session = _make_session(scalars_value=[d1, d2])
        result = await list_dispatches(session, _TENANT, _PROJECT)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_list_type(self):
        session = _make_session(scalars_value=[])
        result = await list_dispatches(session, _TENANT, _PROJECT)
        assert isinstance(result, list)


class TestTransitionDispatchStage:
    @pytest.mark.asyncio
    async def test_stage_updated_on_valid_transition(self):
        dispatch = _make_dispatch(stage="PO_RAISED")
        session = _make_session(scalar_value=dispatch)
        result = await transition_dispatch_stage(session, _TENANT, dispatch.id, "VENDOR_CONFIRMED")
        assert result.current_stage == "VENDOR_CONFIRMED"

    @pytest.mark.asyncio
    async def test_score_updated_on_transition(self):
        dispatch = _make_dispatch(stage="PO_RAISED", score=0.0)
        session = _make_session(scalar_value=dispatch)
        await transition_dispatch_stage(session, _TENANT, dispatch.id, "VENDOR_CONFIRMED")
        # Score should increase after transitioning away from initial stage
        assert dispatch.material_readiness_score > 0.0

    @pytest.mark.asyncio
    async def test_flush_called_on_valid_transition(self):
        dispatch = _make_dispatch(stage="PO_RAISED")
        session = _make_session(scalar_value=dispatch)
        await transition_dispatch_stage(session, _TENANT, dispatch.id, "VENDOR_CONFIRMED")
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self):
        dispatch = _make_dispatch(stage="PO_RAISED")
        session = _make_session(scalar_value=dispatch)
        with pytest.raises(InvalidTransitionError):
            await transition_dispatch_stage(session, _TENANT, dispatch.id, "MANUFACTURING")

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        session = _make_session(scalar_value=None)
        with pytest.raises(DispatchNotFoundError):
            await transition_dispatch_stage(session, _TENANT, uuid.uuid4(), "VENDOR_CONFIRMED")
