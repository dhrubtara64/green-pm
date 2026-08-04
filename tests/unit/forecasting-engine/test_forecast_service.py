"""Tests for Forecasting Engine service layer — S14-01, S14-03."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.forecast.service import ForecastNotFoundError, get_forecast, list_forecasts, upsert_forecast


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


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestUpsertForecastNew:
    @pytest.mark.asyncio
    async def test_creates_new_record_when_none_exists(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "SCHEDULE", 100.0, 95.0, 0.8, "DOWN"
        )
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_new_record_domain_stored(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "BUDGET", 200.0, 195.0, 0.7, "STABLE"
        )
        assert rec.domain == "BUDGET"

    @pytest.mark.asyncio
    async def test_new_record_current_value_stored(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "QUALITY", 50.0, 55.0, 0.9, "UP"
        )
        assert rec.current_value == pytest.approx(50.0)

    @pytest.mark.asyncio
    async def test_new_record_forecast_value_stored(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "RESOURCE", 0.0, 10.0, 0.6, "UP"
        )
        assert rec.forecast_value == pytest.approx(10.0)

    @pytest.mark.asyncio
    async def test_new_record_trend_stored(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "COMMISSIONING", 1.0, 1.0, 0.5, "STABLE"
        )
        assert rec.trend == "STABLE"

    @pytest.mark.asyncio
    async def test_new_record_id_is_uuid(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "CASH_FLOW", 0.0, 0.0, 0.5, "STABLE"
        )
        assert isinstance(rec.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_new_record_computed_at_set(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "SCHEDULE", 0.0, 0.0, 0.5, "STABLE"
        )
        assert rec.computed_at is not None

    @pytest.mark.asyncio
    async def test_new_record_tenant_id_stored(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        rec = await upsert_forecast(
            session, tenant_id, project_id, "BUDGET", 0.0, 0.0, 0.5, "STABLE"
        )
        assert rec.tenant_id == tenant_id


class TestUpsertForecastExisting:
    def _mock_existing(self) -> MagicMock:
        e = MagicMock()
        e.current_value = 100.0
        e.forecast_value = 100.0
        e.confidence = 0.5
        e.trend = "STABLE"
        e.computed_at = None
        return e

    @pytest.mark.asyncio
    async def test_updates_current_value(self, session, tenant_id, project_id):
        existing = self._mock_existing()
        session.scalar.return_value = existing
        await upsert_forecast(
            session, tenant_id, project_id, "SCHEDULE", 80.0, 85.0, 0.9, "UP"
        )
        assert existing.current_value == pytest.approx(80.0)

    @pytest.mark.asyncio
    async def test_updates_trend(self, session, tenant_id, project_id):
        existing = self._mock_existing()
        session.scalar.return_value = existing
        await upsert_forecast(
            session, tenant_id, project_id, "BUDGET", 0.0, 0.0, 0.7, "DOWN"
        )
        assert existing.trend == "DOWN"

    @pytest.mark.asyncio
    async def test_updates_computed_at(self, session, tenant_id, project_id):
        existing = self._mock_existing()
        session.scalar.return_value = existing
        await upsert_forecast(
            session, tenant_id, project_id, "QUALITY", 0.0, 0.0, 0.5, "STABLE"
        )
        assert existing.computed_at is not None

    @pytest.mark.asyncio
    async def test_does_not_call_add(self, session, tenant_id, project_id):
        session.scalar.return_value = self._mock_existing()
        await upsert_forecast(
            session, tenant_id, project_id, "RESOURCE", 0.0, 0.0, 0.5, "STABLE"
        )
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_flushes(self, session, tenant_id, project_id):
        session.scalar.return_value = self._mock_existing()
        await upsert_forecast(
            session, tenant_id, project_id, "COMMISSIONING", 0.0, 0.0, 0.5, "STABLE"
        )
        session.flush.assert_awaited_once()


class TestGetForecast:
    @pytest.mark.asyncio
    async def test_returns_record_when_found(self, session, tenant_id, project_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_forecast(session, tenant_id, project_id, "SCHEDULE")
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        with pytest.raises(ForecastNotFoundError):
            await get_forecast(session, tenant_id, project_id, "BUDGET")

    @pytest.mark.asyncio
    async def test_error_message_contains_domain(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        with pytest.raises(ForecastNotFoundError, match="QUALITY"):
            await get_forecast(session, tenant_id, project_id, "QUALITY")


class TestListForecasts:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_forecasts(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_records(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_forecasts(session, tenant_id, project_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_execute_called_once(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_forecasts(session, tenant_id, project_id)
        session.execute.assert_awaited_once()
