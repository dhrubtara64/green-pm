"""Tests for Green PM Studio service layer — S18-01."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.studio.schemas import BuilderCreate
from app.studio.service import (
    StudioBuilderNotFoundError,
    create_builder,
    deactivate_builder,
    get_builder,
    list_builders,
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
def valid_create(project_id):
    return BuilderCreate(
        project_id=project_id,
        builder_type="WBS_TEMPLATE",
        name="My WBS Config",
        config_data={},
    )


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestCreateBuilder:
    @pytest.mark.asyncio
    async def test_add_called(self, session, tenant_id, valid_create):
        await create_builder(session, tenant_id, valid_create)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self, session, tenant_id, valid_create):
        await create_builder(session, tenant_id, valid_create)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id, valid_create):
        result = await create_builder(session, tenant_id, valid_create)
        assert result is not None

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, valid_create):
        result = await create_builder(session, tenant_id, valid_create)
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_tenant_id_set(self, session, tenant_id, valid_create):
        result = await create_builder(session, tenant_id, valid_create)
        assert result.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_project_id_set(self, session, tenant_id, valid_create, project_id):
        result = await create_builder(session, tenant_id, valid_create)
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_builder_type_set(self, session, tenant_id, valid_create):
        result = await create_builder(session, tenant_id, valid_create)
        assert result.builder_type == "WBS_TEMPLATE"

    @pytest.mark.asyncio
    async def test_name_set(self, session, tenant_id, valid_create):
        result = await create_builder(session, tenant_id, valid_create)
        assert result.name == "My WBS Config"

    @pytest.mark.asyncio
    async def test_is_active_true(self, session, tenant_id, valid_create):
        result = await create_builder(session, tenant_id, valid_create)
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_config_data_merged(self, session, tenant_id, project_id):
        create = BuilderCreate(
            project_id=project_id,
            builder_type="WBS_TEMPLATE",
            name="WBS",
            config_data={"levels": 6},
        )
        result = await create_builder(session, tenant_id, create)
        assert result.config_data["levels"] == 6

    @pytest.mark.asyncio
    async def test_unique_ids_per_call(self, session, tenant_id, valid_create):
        r1 = await create_builder(session, tenant_id, valid_create)
        r2 = await create_builder(session, tenant_id, valid_create)
        assert r1.id != r2.id


class TestGetBuilder:
    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_builder(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(StudioBuilderNotFoundError):
            await get_builder(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_id(self, session, tenant_id):
        session.scalar.return_value = None
        bid = uuid.uuid4()
        with pytest.raises(StudioBuilderNotFoundError, match=str(bid)):
            await get_builder(session, tenant_id, bid)

    @pytest.mark.asyncio
    async def test_scalar_called(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await get_builder(session, tenant_id, uuid.uuid4())
        session.scalar.assert_awaited_once()


class TestListBuilders:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_builders(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_called(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_builders(session, tenant_id, project_id)
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_multiple(self, session, tenant_id, project_id):
        items = [MagicMock() for _ in range(3)]
        session.execute.return_value = _mock_rows(items)
        result = await list_builders(session, tenant_id, project_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_returns_list_type(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_builders(session, tenant_id, project_id)
        assert isinstance(result, list)


class TestDeactivateBuilder:
    @pytest.mark.asyncio
    async def test_sets_is_active_false(self, session, tenant_id):
        existing = MagicMock()
        existing.is_active = True
        session.scalar.return_value = existing
        result = await deactivate_builder(session, tenant_id, uuid.uuid4())
        assert existing.is_active is False

    @pytest.mark.asyncio
    async def test_flush_called(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await deactivate_builder(session, tenant_id, uuid.uuid4())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        existing = MagicMock()
        session.scalar.return_value = existing
        result = await deactivate_builder(session, tenant_id, uuid.uuid4())
        assert result is existing

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(StudioBuilderNotFoundError):
            await deactivate_builder(session, tenant_id, uuid.uuid4())
