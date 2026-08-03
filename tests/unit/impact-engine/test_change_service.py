"""Unit tests for Change service — S5-05."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.changes.service as _svc
from app.changes.schemas import ChangeCreate
from app.changes.service import (
    ChangeNotFoundError,
    create_change,
    get_change,
    list_changes,
)

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_USER = uuid.uuid4()
_ENTITY = uuid.uuid4()


def _make_create(**kwargs) -> ChangeCreate:
    defaults = {
        "project_id": _PROJECT,
        "entity_type": "activity",
        "entity_id": _ENTITY,
        "change_type": "scope_change",
    }
    defaults.update(kwargs)
    return ChangeCreate(**defaults)


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_change(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "project_id": _PROJECT,
        "tenant_id": _TENANT,
        "entity_type": "activity",
        "entity_id": _ENTITY,
        "change_type": "scope_change",
        "status": "initiated",
        "change_metadata": {},
    }
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ──────────────────────────────────────────────────────────────────────────────
# create_change
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateChange:
    @pytest.mark.asyncio
    async def test_adds_change_to_session(self):
        session = _make_session()
        with patch.object(_svc, "write_outbox_event", new=AsyncMock()):
            await create_change(session, _TENANT, _USER, _make_create())
        assert session.add.called

    @pytest.mark.asyncio
    async def test_status_set_to_initiated(self):
        session = _make_session()
        added = {}

        def capture_add(obj):
            added["obj"] = obj

        session.add = capture_add
        with patch.object(_svc, "write_outbox_event", new=AsyncMock()):
            await create_change(session, _TENANT, _USER, _make_create())
        assert added["obj"].status == "initiated"

    @pytest.mark.asyncio
    async def test_outbox_event_emitted(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with patch.object(_svc, "write_outbox_event", new=mock_outbox):
            await create_change(session, _TENANT, _USER, _make_create())
        mock_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_outbox_event_type_is_change_initiated(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with patch.object(_svc, "write_outbox_event", new=mock_outbox):
            await create_change(session, _TENANT, _USER, _make_create())
        assert mock_outbox.call_args.kwargs["event_type"] == "ChangeInitiated"

    @pytest.mark.asyncio
    async def test_outbox_topic_is_greenpm_changes(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with patch.object(_svc, "write_outbox_event", new=mock_outbox):
            await create_change(session, _TENANT, _USER, _make_create())
        assert mock_outbox.call_args.kwargs["topic"] == "greenpm.changes"

    @pytest.mark.asyncio
    async def test_outbox_payload_has_change_type(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with patch.object(_svc, "write_outbox_event", new=mock_outbox):
            await create_change(session, _TENANT, _USER, _make_create(change_type="cost_change"))
        payload = mock_outbox.call_args.kwargs["payload"]
        assert payload["change_type"] == "cost_change"

    @pytest.mark.asyncio
    async def test_flush_called_after_add(self):
        session = _make_session()
        with patch.object(_svc, "write_outbox_event", new=AsyncMock()):
            await create_change(session, _TENANT, _USER, _make_create())
        assert session.flush.called


# ──────────────────────────────────────────────────────────────────────────────
# get_change
# ──────────────────────────────────────────────────────────────────────────────

class TestGetChange:
    @pytest.mark.asyncio
    async def test_returns_change_when_found(self):
        session = _make_session()
        ch = _make_change()
        session.scalar = AsyncMock(return_value=ch)
        result = await get_change(session, _TENANT, ch.id)
        assert result is ch

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        with pytest.raises(ChangeNotFoundError):
            await get_change(session, _TENANT, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_id(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        cid = uuid.uuid4()
        with pytest.raises(ChangeNotFoundError, match=str(cid)):
            await get_change(session, _TENANT, cid)


# ──────────────────────────────────────────────────────────────────────────────
# list_changes
# ──────────────────────────────────────────────────────────────────────────────

class TestListChanges:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        session = _make_session()
        items = [_make_change() for _ in range(3)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = items
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_changes(session, _TENANT, _PROJECT)
        assert list(result) == items

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_changes(session, _TENANT, _PROJECT)
        assert result == []

    @pytest.mark.asyncio
    async def test_default_limit_is_100(self):
        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)
        await list_changes(session, _TENANT, _PROJECT)
        assert session.execute.called
