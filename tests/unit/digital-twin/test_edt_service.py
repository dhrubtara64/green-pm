"""Tests for EDT synthesis service layer — S17-02, S17-04."""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.twin.schemas import EDTSynthesisCreate
from app.twin.service import (
    EDTNotFoundError,
    create_edt_synthesis,
    get_current_edt,
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
    return EDTSynthesisCreate(
        project_id=project_id,
        synthesis_date=date(2026, 8, 4),
        reality_panel={"risk_count": 3, "milestone_health": "ON_TRACK"},
        forecast_panel={"completion_date": "2026-12-01"},
        decisions_panel={"pending_approvals": 2},
    )


class TestCreateEDTSynthesis:
    @pytest.mark.asyncio
    async def test_add_called(self, session, tenant_id, valid_create):
        await create_edt_synthesis(session, tenant_id, valid_create)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self, session, tenant_id, valid_create):
        await create_edt_synthesis(session, tenant_id, valid_create)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result is not None

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_tenant_id_set(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_project_id_set(self, session, tenant_id, valid_create, project_id):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_synthesis_date_set(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.synthesis_date == date(2026, 8, 4)

    @pytest.mark.asyncio
    async def test_reality_panel_set(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.reality_panel == {"risk_count": 3, "milestone_health": "ON_TRACK"}

    @pytest.mark.asyncio
    async def test_forecast_panel_set(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.forecast_panel == {"completion_date": "2026-12-01"}

    @pytest.mark.asyncio
    async def test_decisions_panel_set(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.decisions_panel == {"pending_approvals": 2}

    @pytest.mark.asyncio
    async def test_synthesized_at_set(self, session, tenant_id, valid_create):
        result = await create_edt_synthesis(session, tenant_id, valid_create)
        assert result.synthesized_at is not None

    @pytest.mark.asyncio
    async def test_unique_ids_per_call(self, session, tenant_id, valid_create):
        r1 = await create_edt_synthesis(session, tenant_id, valid_create)
        r2 = await create_edt_synthesis(session, tenant_id, valid_create)
        assert r1.id != r2.id


class TestGetCurrentEDT:
    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id, project_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_current_edt(session, tenant_id, project_id)
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        with pytest.raises(EDTNotFoundError):
            await get_current_edt(session, tenant_id, project_id)

    @pytest.mark.asyncio
    async def test_error_message_contains_project_id(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        with pytest.raises(EDTNotFoundError, match=str(project_id)):
            await get_current_edt(session, tenant_id, project_id)

    @pytest.mark.asyncio
    async def test_scalar_called(self, session, tenant_id, project_id):
        session.scalar.return_value = MagicMock()
        await get_current_edt(session, tenant_id, project_id)
        session.scalar.assert_awaited_once()
