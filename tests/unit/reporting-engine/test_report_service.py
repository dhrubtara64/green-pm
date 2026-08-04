"""Tests for Reporting Engine service layer — S17-01, S17-04, S17-05."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.reporting.schemas import ReportCreate
from app.reporting.service import (
    ReportNotFoundError,
    create_report,
    generate_report,
    get_report,
    list_reports,
    schedule_report,
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
    return ReportCreate(
        project_id=project_id,
        report_type="WEEKLY_SUMMARY",
        title="Week 21 Project Report",
        structured_data={"risks": 3, "delays": 1},
    )


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestCreateReport:
    @pytest.mark.asyncio
    async def test_add_called(self, session, tenant_id, valid_create):
        await create_report(session, tenant_id, valid_create)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self, session, tenant_id, valid_create):
        await create_report(session, tenant_id, valid_create)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_report(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result is not None

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_status_is_pending(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result.status == "PENDING"

    @pytest.mark.asyncio
    async def test_tenant_id_set(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_report_type_set(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result.report_type == "WEEKLY_SUMMARY"

    @pytest.mark.asyncio
    async def test_title_set(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result.title == "Week 21 Project Report"

    @pytest.mark.asyncio
    async def test_scheduled_false_by_default(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result.scheduled is False

    @pytest.mark.asyncio
    async def test_structured_data_stored(self, session, tenant_id, valid_create):
        result = await create_report(session, tenant_id, valid_create)
        assert result.structured_data == {"risks": 3, "delays": 1}

    @pytest.mark.asyncio
    async def test_unique_ids_per_call(self, session, tenant_id, valid_create):
        r1 = await create_report(session, tenant_id, valid_create)
        r2 = await create_report(session, tenant_id, valid_create)
        assert r1.id != r2.id


class TestGenerateReport:
    @pytest.fixture
    def mock_report(self):
        r = MagicMock()
        r.status = "PENDING"
        r.report_type = "WEEKLY_SUMMARY"
        r.title = "My Report"
        r.structured_data = {}
        return r

    @pytest.mark.asyncio
    async def test_status_becomes_complete(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        await generate_report(session, tenant_id, uuid.uuid4())
        assert mock_report.status == "COMPLETE"

    @pytest.mark.asyncio
    async def test_narrative_set(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        await generate_report(session, tenant_id, uuid.uuid4())
        assert mock_report.narrative is not None
        assert len(mock_report.narrative) > 0

    @pytest.mark.asyncio
    async def test_generated_at_set(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        await generate_report(session, tenant_id, uuid.uuid4())
        assert mock_report.generated_at is not None

    @pytest.mark.asyncio
    async def test_evidence_chain_id_set(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        await generate_report(session, tenant_id, uuid.uuid4())
        assert isinstance(mock_report.evidence_chain_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_flush_called_multiple_times(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        await generate_report(session, tenant_id, uuid.uuid4())
        assert session.flush.await_count >= 2

    @pytest.mark.asyncio
    async def test_with_mock_ai_client_uses_response(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value="AI narrative text.")
        await generate_report(session, tenant_id, uuid.uuid4(), ai_client=mock_client)
        assert mock_report.narrative == "AI narrative text."

    @pytest.mark.asyncio
    async def test_with_mock_ai_client_calls_complete(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value="AI text.")
        await generate_report(session, tenant_id, uuid.uuid4(), ai_client=mock_client)
        mock_client.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found_raises(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(ReportNotFoundError):
            await generate_report(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_ai_client_failure_sets_failed_status(self, session, tenant_id, mock_report):
        session.scalar.return_value = mock_report
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(side_effect=RuntimeError("API down"))
        with pytest.raises(RuntimeError):
            await generate_report(session, tenant_id, uuid.uuid4(), ai_client=mock_client)
        assert mock_report.status == "FAILED"

    @pytest.mark.asyncio
    async def test_status_becomes_generating_then_complete(self, session, tenant_id, mock_report):
        status_history = []
        original_flush = session.flush

        async def tracking_flush():
            status_history.append(mock_report.status)

        session.flush.side_effect = tracking_flush
        session.scalar.return_value = mock_report
        await generate_report(session, tenant_id, uuid.uuid4())
        assert "GENERATING" in status_history


class TestListReports:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_reports(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_called(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_reports(session, tenant_id, project_id)
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_multiple(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_reports(session, tenant_id, project_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_report_type_filter_accepted(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_reports(session, tenant_id, project_id, report_type="RISK_DIGEST")
        session.execute.assert_awaited_once()


class TestGetReport:
    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_report(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(ReportNotFoundError):
            await get_report(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_id(self, session, tenant_id):
        session.scalar.return_value = None
        rid = uuid.uuid4()
        with pytest.raises(ReportNotFoundError, match=str(rid)):
            await get_report(session, tenant_id, rid)


class TestScheduleReport:
    @pytest.mark.asyncio
    async def test_add_called(self, session, tenant_id, project_id):
        await schedule_report(session, tenant_id, project_id, "WEEKLY_SUMMARY")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduled_flag_true(self, session, tenant_id, project_id):
        result = await schedule_report(session, tenant_id, project_id, "WEEKLY_SUMMARY")
        assert result.scheduled is True

    @pytest.mark.asyncio
    async def test_report_type_set(self, session, tenant_id, project_id):
        result = await schedule_report(session, tenant_id, project_id, "RISK_DIGEST")
        assert result.report_type == "RISK_DIGEST"

    @pytest.mark.asyncio
    async def test_title_auto_generated(self, session, tenant_id, project_id):
        result = await schedule_report(session, tenant_id, project_id, "WEEKLY_SUMMARY")
        assert len(result.title) > 0

    @pytest.mark.asyncio
    async def test_custom_title_used(self, session, tenant_id, project_id):
        result = await schedule_report(
            session, tenant_id, project_id, "WEEKLY_SUMMARY", title="Custom Title"
        )
        assert result.title == "Custom Title"

    @pytest.mark.asyncio
    async def test_status_is_pending(self, session, tenant_id, project_id):
        result = await schedule_report(session, tenant_id, project_id, "WEEKLY_SUMMARY")
        assert result.status == "PENDING"
