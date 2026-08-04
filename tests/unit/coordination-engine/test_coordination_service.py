"""Tests for Coordination Engine service layer — S12-04, S12-05."""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.coordination.schemas import CoordinationItemCreate, CoordinationSummaryResponse
from app.coordination.pipeline_engine import InvalidTransitionError
from app.coordination.service import (
    CoordinationItemNotFoundError,
    close_item,
    create_coordination_item,
    get_coordination_item,
    get_overdue_items,
    get_summary,
    list_coordination_items,
    transition_status,
)


@pytest.fixture
def session():
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.scalar = AsyncMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


def _create(project_id: uuid.UUID, title: str = "Test item", **kwargs) -> CoordinationItemCreate:
    return CoordinationItemCreate(project_id=project_id, title=title, **kwargs)


def _mock_item(status: str = "OPEN", due_date=None, project_id=None) -> MagicMock:
    item = MagicMock()
    item.status = status
    item.due_date = due_date
    item.project_id = project_id or uuid.uuid4()
    item.stage_timestamps = {"OPEN": None}
    return item


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


# ---------------------------------------------------------------------------
# create_coordination_item
# ---------------------------------------------------------------------------

class TestCreateCoordinationItem:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_coordination_item(session, tenant_id, _create(project_id))
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await create_coordination_item(session, tenant_id, _create(project_id))
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_status_is_open(self, session, tenant_id, project_id):
        item = await create_coordination_item(session, tenant_id, _create(project_id))
        assert item.status == "OPEN"

    @pytest.mark.asyncio
    async def test_title_stored(self, session, tenant_id, project_id):
        item = await create_coordination_item(session, tenant_id, _create(project_id, title="Risk"))
        assert item.title == "Risk"

    @pytest.mark.asyncio
    async def test_project_id_stored(self, session, tenant_id, project_id):
        item = await create_coordination_item(session, tenant_id, _create(project_id))
        assert item.project_id == project_id

    @pytest.mark.asyncio
    async def test_tenant_id_stored(self, session, tenant_id, project_id):
        item = await create_coordination_item(session, tenant_id, _create(project_id))
        assert item.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_source_event_id_stored(self, session, tenant_id, project_id):
        item = await create_coordination_item(
            session, tenant_id, _create(project_id, source_event_id="evt-abc")
        )
        assert item.source_event_id == "evt-abc"

    @pytest.mark.asyncio
    async def test_stage_timestamps_initialized(self, session, tenant_id, project_id):
        item = await create_coordination_item(session, tenant_id, _create(project_id))
        assert isinstance(item.stage_timestamps, dict)
        assert "OPEN" in item.stage_timestamps


# ---------------------------------------------------------------------------
# get_coordination_item
# ---------------------------------------------------------------------------

class TestGetCoordinationItem:
    @pytest.mark.asyncio
    async def test_returns_item_when_found(self, session, tenant_id):
        mock_item = MagicMock()
        session.scalar.return_value = mock_item
        result = await get_coordination_item(session, tenant_id, uuid.uuid4())
        assert result is mock_item

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(CoordinationItemNotFoundError):
            await get_coordination_item(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_item_id(self, session, tenant_id):
        session.scalar.return_value = None
        iid = uuid.uuid4()
        with pytest.raises(CoordinationItemNotFoundError, match=str(iid)):
            await get_coordination_item(session, tenant_id, iid)


# ---------------------------------------------------------------------------
# list_coordination_items
# ---------------------------------------------------------------------------

class TestListCoordinationItems:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_coordination_items(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_items(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_coordination_items(session, tenant_id, project_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_status_filter_passed(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_coordination_items(session, tenant_id, project_id, status="OPEN")
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assignee_filter_passed(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_coordination_items(session, tenant_id, project_id, assignee_id=uuid.uuid4())
        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# transition_status
# ---------------------------------------------------------------------------

class TestTransitionStatus:
    @pytest.mark.asyncio
    async def test_valid_transition_updates_status(self, session, tenant_id):
        mock_item = _mock_item("OPEN")
        session.scalar.return_value = mock_item
        await transition_status(session, tenant_id, uuid.uuid4(), "ACKNOWLEDGED")
        assert mock_item.status == "ACKNOWLEDGED"

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id):
        mock_item = _mock_item("OPEN")
        session.scalar.return_value = mock_item
        await transition_status(session, tenant_id, uuid.uuid4(), "ACKNOWLEDGED")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stage_timestamp_recorded(self, session, tenant_id):
        mock_item = _mock_item("OPEN")
        session.scalar.return_value = mock_item
        await transition_status(session, tenant_id, uuid.uuid4(), "ACKNOWLEDGED", "2026-08-04T12:00:00Z")
        assert "ACKNOWLEDGED" in mock_item.stage_timestamps

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self, session, tenant_id):
        mock_item = _mock_item("OPEN")
        session.scalar.return_value = mock_item
        with pytest.raises(InvalidTransitionError):
            await transition_status(session, tenant_id, uuid.uuid4(), "CLOSED")

    @pytest.mark.asyncio
    async def test_not_found_raises(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(CoordinationItemNotFoundError):
            await transition_status(session, tenant_id, uuid.uuid4(), "ACKNOWLEDGED")

    @pytest.mark.asyncio
    async def test_full_chain_transitions(self, session, tenant_id):
        mock_item = _mock_item("OPEN")
        session.scalar.return_value = mock_item

        for to_status in ("ACKNOWLEDGED", "EXECUTING", "VERIFIED", "CLOSED"):
            await transition_status(session, tenant_id, uuid.uuid4(), to_status)
            assert mock_item.status == to_status


# ---------------------------------------------------------------------------
# close_item
# ---------------------------------------------------------------------------

class TestCloseItem:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id):
        mock_item = _mock_item("VERIFIED")
        session.scalar.return_value = mock_item
        await close_item(session, tenant_id, uuid.uuid4())
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id):
        mock_item = _mock_item("VERIFIED")
        session.scalar.return_value = mock_item
        await close_item(session, tenant_id, uuid.uuid4())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_closed_by_stored(self, session, tenant_id):
        mock_item = _mock_item()
        session.scalar.return_value = mock_item
        closure = await close_item(session, tenant_id, uuid.uuid4(), closed_by="user@example.com")
        assert closure.closed_by == "user@example.com"

    @pytest.mark.asyncio
    async def test_resolution_notes_stored(self, session, tenant_id):
        mock_item = _mock_item()
        session.scalar.return_value = mock_item
        closure = await close_item(session, tenant_id, uuid.uuid4(),
                                   resolution_notes="Issue resolved by PM")
        assert closure.resolution_notes == "Issue resolved by PM"


# ---------------------------------------------------------------------------
# get_overdue_items (S12-05)
# ---------------------------------------------------------------------------

class TestGetOverdueItems:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_items(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert result == []

    @pytest.mark.asyncio
    async def test_overdue_open_item_returned(self, session, tenant_id, project_id):
        overdue_item = _mock_item("OPEN", due_date=date(2026, 7, 1))
        session.execute.return_value = _mock_rows([overdue_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_future_due_date_not_returned(self, session, tenant_id, project_id):
        future_item = _mock_item("OPEN", due_date=date(2026, 12, 1))
        session.execute.return_value = _mock_rows([future_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert result == []

    @pytest.mark.asyncio
    async def test_verified_item_not_returned_even_if_past_due(self, session, tenant_id, project_id):
        verified_item = _mock_item("VERIFIED", due_date=date(2026, 7, 1))
        session.execute.return_value = _mock_rows([verified_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert result == []

    @pytest.mark.asyncio
    async def test_closed_item_not_returned_even_if_past_due(self, session, tenant_id, project_id):
        closed_item = _mock_item("CLOSED", due_date=date(2026, 7, 1))
        session.execute.return_value = _mock_rows([closed_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert result == []

    @pytest.mark.asyncio
    async def test_no_due_date_not_returned(self, session, tenant_id, project_id):
        no_date_item = _mock_item("OPEN", due_date=None)
        session.execute.return_value = _mock_rows([no_date_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert result == []

    @pytest.mark.asyncio
    async def test_acknowledged_overdue_returned(self, session, tenant_id, project_id):
        ack_item = _mock_item("ACKNOWLEDGED", due_date=date(2026, 7, 1))
        session.execute.return_value = _mock_rows([ack_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_executing_overdue_returned(self, session, tenant_id, project_id):
        exec_item = _mock_item("EXECUTING", due_date=date(2026, 7, 1))
        session.execute.return_value = _mock_rows([exec_item])
        result = await get_overdue_items(session, tenant_id, project_id, date(2026, 8, 4))
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_summary (S12-05)
# ---------------------------------------------------------------------------

class TestGetSummary:
    @pytest.mark.asyncio
    async def test_returns_summary_response(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_summary(session, tenant_id, project_id, date(2026, 8, 4))
        assert isinstance(result, CoordinationSummaryResponse)

    @pytest.mark.asyncio
    async def test_total_zero_for_empty(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_summary(session, tenant_id, project_id, date(2026, 8, 4))
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_overdue_count_zero_for_empty(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_summary(session, tenant_id, project_id, date(2026, 8, 4))
        assert result.overdue_count == 0

    @pytest.mark.asyncio
    async def test_total_counts_all_items(self, session, tenant_id, project_id):
        items = [_mock_item("OPEN"), _mock_item("ACKNOWLEDGED"), _mock_item("CLOSED")]
        # get_summary calls list + get_overdue, both use session.execute
        call_count = 0

        async def execute_side(stmt):
            nonlocal call_count
            call_count += 1
            return _mock_rows(items)

        session.execute.side_effect = execute_side
        result = await get_summary(session, tenant_id, project_id, date(2026, 8, 4))
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_by_status_populated(self, session, tenant_id, project_id):
        items = [_mock_item("OPEN"), _mock_item("OPEN"), _mock_item("CLOSED")]

        async def execute_side(stmt):
            return _mock_rows(items)

        session.execute.side_effect = execute_side
        result = await get_summary(session, tenant_id, project_id, date(2026, 8, 4))
        assert result.by_status.get("OPEN", 0) == 2
        assert result.by_status.get("CLOSED", 0) == 1

    @pytest.mark.asyncio
    async def test_open_count_excludes_terminal(self, session, tenant_id, project_id):
        items = [_mock_item("OPEN"), _mock_item("VERIFIED"), _mock_item("CLOSED")]

        async def execute_side(stmt):
            return _mock_rows(items)

        session.execute.side_effect = execute_side
        result = await get_summary(session, tenant_id, project_id, date(2026, 8, 4))
        assert result.open_count == 1
