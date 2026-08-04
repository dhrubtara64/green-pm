"""Tests for Command Centre service layer — S17-03, S17-04."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.twin.schemas import COMMAND_CENTRE_PANELS, CommandCentrePanelCreate
from app.twin.service import (
    CommandCentrePanelNotFoundError,
    get_command_centre_panel,
    list_command_centre_panels,
    update_command_centre_panel,
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


@pytest.fixture
def valid_panel_create(project_id):
    return CommandCentrePanelCreate(
        project_id=project_id,
        panel_name="RISKS",
        panel_data={"high_risks": 2, "medium_risks": 5},
        triggered_by_event="risk.updated",
    )


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestUpdateCommandCentrePanel:
    @pytest.mark.asyncio
    async def test_creates_new_panel_when_none_exists(
        self, session, tenant_id, valid_panel_create
    ):
        session.scalar.return_value = None
        result = await update_command_centre_panel(session, tenant_id, valid_panel_create)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called_on_create(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = None
        await update_command_centre_panel(session, tenant_id, valid_panel_create)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_new_panel_id_is_uuid(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = None
        result = await update_command_centre_panel(session, tenant_id, valid_panel_create)
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_new_panel_name_set(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = None
        result = await update_command_centre_panel(session, tenant_id, valid_panel_create)
        assert result.panel_name == "RISKS"

    @pytest.mark.asyncio
    async def test_new_panel_data_set(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = None
        result = await update_command_centre_panel(session, tenant_id, valid_panel_create)
        assert result.panel_data == {"high_risks": 2, "medium_risks": 5}

    @pytest.mark.asyncio
    async def test_new_panel_updated_at_set(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = None
        result = await update_command_centre_panel(session, tenant_id, valid_panel_create)
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_new_panel_triggered_by_event_set(
        self, session, tenant_id, valid_panel_create
    ):
        session.scalar.return_value = None
        result = await update_command_centre_panel(session, tenant_id, valid_panel_create)
        assert result.triggered_by_event == "risk.updated"

    @pytest.mark.asyncio
    async def test_updates_existing_panel(self, session, tenant_id, project_id):
        existing = MagicMock()
        existing.panel_data = {"old": "data"}
        session.scalar.return_value = existing

        create = CommandCentrePanelCreate(
            project_id=project_id,
            panel_name="RISKS",
            panel_data={"new": "data"},
        )
        result = await update_command_centre_panel(session, tenant_id, create)
        assert existing.panel_data == {"new": "data"}
        assert result is existing

    @pytest.mark.asyncio
    async def test_existing_panel_not_added_again(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = MagicMock()
        await update_command_centre_panel(session, tenant_id, valid_panel_create)
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_panel_flush_called(self, session, tenant_id, valid_panel_create):
        session.scalar.return_value = MagicMock()
        await update_command_centre_panel(session, tenant_id, valid_panel_create)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_existing_panel_updated_at_refreshed(
        self, session, tenant_id, valid_panel_create
    ):
        existing = MagicMock()
        existing.updated_at = None
        session.scalar.return_value = existing
        await update_command_centre_panel(session, tenant_id, valid_panel_create)
        assert existing.updated_at is not None

    @pytest.mark.asyncio
    async def test_all_panels_can_be_updated(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        for panel in COMMAND_CENTRE_PANELS:
            create = CommandCentrePanelCreate(
                project_id=project_id,
                panel_name=panel,
                panel_data={},
            )
            result = await update_command_centre_panel(session, tenant_id, create)
            assert result.panel_name == panel


class TestGetCommandCentrePanel:
    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id, project_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_command_centre_panel(session, tenant_id, project_id, "RISKS")
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        with pytest.raises(CommandCentrePanelNotFoundError):
            await get_command_centre_panel(session, tenant_id, project_id, "RISKS")

    @pytest.mark.asyncio
    async def test_error_message_contains_panel_name(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        with pytest.raises(CommandCentrePanelNotFoundError, match="VENDORS"):
            await get_command_centre_panel(session, tenant_id, project_id, "VENDORS")

    @pytest.mark.asyncio
    async def test_scalar_called(self, session, tenant_id, project_id):
        session.scalar.return_value = MagicMock()
        await get_command_centre_panel(session, tenant_id, project_id, "DECISIONS")
        session.scalar.assert_awaited_once()


class TestListCommandCentrePanels:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_command_centre_panels(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_called(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_command_centre_panels(session, tenant_id, project_id)
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_multiple_panels(self, session, tenant_id, project_id):
        items = [MagicMock() for _ in range(8)]
        session.execute.return_value = _mock_rows(items)
        result = await list_command_centre_panels(session, tenant_id, project_id)
        assert len(result) == 8

    @pytest.mark.asyncio
    async def test_returns_list_type(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_command_centre_panels(session, tenant_id, project_id)
        assert isinstance(result, list)
