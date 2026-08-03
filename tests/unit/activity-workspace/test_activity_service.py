"""Unit tests for Activity service — S2-WS-01."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.activities.service as _svc
from app.activities.schemas import ActivityCreate, ActivityUpdate
from app.activities.service import (
    ActivityNotFoundError,
    create_activity,
    get_activity,
    list_activities,
    update_activity,
)


def _make_activity(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Pile Foundation",
        "wbs_code": None,
        "status": "not_started",
        "progress_pct": 0.0,
        "planned_start": None,
        "planned_finish": None,
        "pig_node_id": None,
    }
    defaults.update(kwargs)
    m = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ──────────────────────────────────────────────────────────────────────────────
# create_activity
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateActivity:
    @pytest.fixture
    def tenant_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def node(self):
        n = MagicMock()
        n.id = uuid.uuid4()
        return n

    def _data(self, **kwargs):
        defaults = {
            "project_id": uuid.uuid4(),
            "name": "Foundation Works",
        }
        defaults.update(kwargs)
        return ActivityCreate(**defaults)

    @pytest.mark.asyncio
    async def test_create_calls_flush_twice(self, tenant_id, node):
        session = _make_session()
        data = self._data()
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=node)),
            patch.object(_svc, "write_outbox_event", new=AsyncMock()),
        ):
            await create_activity(session, tenant_id, data)
        assert session.flush.call_count == 2

    @pytest.mark.asyncio
    async def test_create_adds_activity_to_session(self, tenant_id, node):
        session = _make_session()
        data = self._data()
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=node)),
            patch.object(_svc, "write_outbox_event", new=AsyncMock()),
        ):
            await create_activity(session, tenant_id, data)
        assert session.add.called

    @pytest.mark.asyncio
    async def test_create_calls_sync_entity(self, tenant_id, node):
        session = _make_session()
        data = self._data()
        mock_sync = AsyncMock(return_value=node)
        with (
            patch.object(_svc, "sync_entity", new=mock_sync),
            patch.object(_svc, "write_outbox_event", new=AsyncMock()),
        ):
            await create_activity(session, tenant_id, data)
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args.kwargs
        assert call_kwargs["entity_type"] == "activity"
        assert call_kwargs["tenant_id"] == tenant_id

    @pytest.mark.asyncio
    async def test_create_calls_write_outbox_event(self, tenant_id, node):
        session = _make_session()
        data = self._data()
        mock_outbox = AsyncMock()
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=node)),
            patch.object(_svc, "write_outbox_event", new=mock_outbox),
        ):
            await create_activity(session, tenant_id, data)
        mock_outbox.assert_called_once()
        call_kwargs = mock_outbox.call_args.kwargs
        assert call_kwargs["event_type"] == "ActivityCreated"
        assert call_kwargs["tenant_id"] == tenant_id

    @pytest.mark.asyncio
    async def test_create_outbox_topic_is_activities(self, tenant_id, node):
        session = _make_session()
        data = self._data()
        mock_outbox = AsyncMock()
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=node)),
            patch.object(_svc, "write_outbox_event", new=mock_outbox),
        ):
            await create_activity(session, tenant_id, data)
        assert mock_outbox.call_args.kwargs["topic"] == "greenpm.activities"

    @pytest.mark.asyncio
    async def test_create_refreshes_activity(self, tenant_id, node):
        session = _make_session()
        data = self._data()
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=node)),
            patch.object(_svc, "write_outbox_event", new=AsyncMock()),
        ):
            await create_activity(session, tenant_id, data)
        assert session.refresh.called


# ──────────────────────────────────────────────────────────────────────────────
# get_activity
# ──────────────────────────────────────────────────────────────────────────────

class TestGetActivity:
    @pytest.mark.asyncio
    async def test_returns_activity_when_found(self):
        tenant_id = uuid.uuid4()
        activity = _make_activity(tenant_id=tenant_id)
        session = _make_session()
        session.scalar = AsyncMock(return_value=activity)
        result = await get_activity(session, tenant_id, activity.id)
        assert result is activity

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        with pytest.raises(ActivityNotFoundError):
            await get_activity(session, uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_not_found_error_message_contains_id(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        activity_id = uuid.uuid4()
        with pytest.raises(ActivityNotFoundError, match=str(activity_id)):
            await get_activity(session, uuid.uuid4(), activity_id)


# ──────────────────────────────────────────────────────────────────────────────
# list_activities
# ──────────────────────────────────────────────────────────────────────────────

class TestListActivities:
    @pytest.mark.asyncio
    async def test_returns_sequence(self):
        session = _make_session()
        activities = [_make_activity() for _ in range(3)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = activities
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_activities(session, uuid.uuid4(), uuid.uuid4())
        assert list(result) == activities

    @pytest.mark.asyncio
    async def test_empty_list(self):
        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_activities(session, uuid.uuid4(), uuid.uuid4())
        assert list(result) == []


# ──────────────────────────────────────────────────────────────────────────────
# update_activity
# ──────────────────────────────────────────────────────────────────────────────

class TestUpdateActivity:
    @pytest.mark.asyncio
    async def test_update_calls_sync_entity(self):
        tenant_id = uuid.uuid4()
        activity = _make_activity(tenant_id=tenant_id)
        session = _make_session()
        session.scalar = AsyncMock(return_value=activity)
        mock_sync = AsyncMock(return_value=MagicMock())
        mock_outbox = AsyncMock()
        data = ActivityUpdate(status="in_progress")
        with (
            patch.object(_svc, "sync_entity", new=mock_sync),
            patch.object(_svc, "write_outbox_event", new=mock_outbox),
        ):
            await update_activity(session, tenant_id, activity.id, data)
        mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_writes_outbox_event(self):
        tenant_id = uuid.uuid4()
        activity = _make_activity(tenant_id=tenant_id)
        session = _make_session()
        session.scalar = AsyncMock(return_value=activity)
        mock_outbox = AsyncMock()
        data = ActivityUpdate(status="completed", progress_pct=100.0)
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=MagicMock())),
            patch.object(_svc, "write_outbox_event", new=mock_outbox),
        ):
            await update_activity(session, tenant_id, activity.id, data)
        mock_outbox.assert_called_once()
        call_kwargs = mock_outbox.call_args.kwargs
        assert call_kwargs["event_type"] == "ActivityUpdated"

    @pytest.mark.asyncio
    async def test_update_not_found_raises(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        with pytest.raises(ActivityNotFoundError):
            await update_activity(session, uuid.uuid4(), uuid.uuid4(), ActivityUpdate())

    @pytest.mark.asyncio
    async def test_update_applies_changed_fields(self):
        tenant_id = uuid.uuid4()
        activity = _make_activity(tenant_id=tenant_id, status="not_started")
        session = _make_session()
        session.scalar = AsyncMock(return_value=activity)
        data = ActivityUpdate(status="in_progress")
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=MagicMock())),
            patch.object(_svc, "write_outbox_event", new=AsyncMock()),
        ):
            await update_activity(session, tenant_id, activity.id, data)
        assert activity.status == "in_progress"

    @pytest.mark.asyncio
    async def test_update_outbox_payload_contains_changes(self):
        tenant_id = uuid.uuid4()
        activity = _make_activity(tenant_id=tenant_id)
        session = _make_session()
        session.scalar = AsyncMock(return_value=activity)
        mock_outbox = AsyncMock()
        data = ActivityUpdate(progress_pct=55.0)
        with (
            patch.object(_svc, "sync_entity", new=AsyncMock(return_value=MagicMock())),
            patch.object(_svc, "write_outbox_event", new=mock_outbox),
        ):
            await update_activity(session, tenant_id, activity.id, data)
        payload = mock_outbox.call_args.kwargs["payload"]
        assert "progress_pct" in payload["changes"]
