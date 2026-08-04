"""Tests for Organizational Alignment Engine service layer — S14-04, S14-05, S14-06."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.alignment.schemas import (
    AlignmentGapResult,
    AlignmentMapResponse,
    AlignmentReceiptCreate,
    StakeholderAlignmentStatus,
)
from app.alignment.service import (
    AlignmentReceiptNotFoundError,
    confirm_acknowledgment,
    confirm_receipt,
    get_alignment_gaps,
    get_alignment_map,
    list_alignment,
    record_information_sent,
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


def _create(project_id: uuid.UUID, **kw) -> AlignmentReceiptCreate:
    return AlignmentReceiptCreate(
        project_id=project_id,
        stakeholder_id=kw.get("stakeholder_id", uuid.uuid4()),
        event_id=kw.get("event_id", "evt-001"),
        event_type=kw.get("event_type", "RiskIdentified"),
    )


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestRecordInformationSent:
    @pytest.mark.asyncio
    async def test_calls_add(self, session, tenant_id, project_id):
        await record_information_sent(session, tenant_id, _create(project_id))
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await record_information_sent(session, tenant_id, _create(project_id))
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, project_id):
        rec = await record_information_sent(session, tenant_id, _create(project_id))
        assert isinstance(rec.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_sent_at_is_set(self, session, tenant_id, project_id):
        rec = await record_information_sent(session, tenant_id, _create(project_id))
        assert rec.sent_at is not None

    @pytest.mark.asyncio
    async def test_tenant_id_stored(self, session, tenant_id, project_id):
        rec = await record_information_sent(session, tenant_id, _create(project_id))
        assert rec.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_project_id_stored(self, session, tenant_id, project_id):
        rec = await record_information_sent(session, tenant_id, _create(project_id))
        assert rec.project_id == project_id

    @pytest.mark.asyncio
    async def test_event_type_stored(self, session, tenant_id, project_id):
        rec = await record_information_sent(
            session, tenant_id, _create(project_id, event_type="CriticalPathChanged")
        )
        assert rec.event_type == "CriticalPathChanged"

    @pytest.mark.asyncio
    async def test_event_id_stored(self, session, tenant_id, project_id):
        rec = await record_information_sent(
            session, tenant_id, _create(project_id, event_id="evt-xyz")
        )
        assert rec.event_id == "evt-xyz"


class TestConfirmReceipt:
    @pytest.mark.asyncio
    async def test_returns_receipt(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await confirm_receipt(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_sets_receipt_confirmed_at(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        await confirm_receipt(session, tenant_id, uuid.uuid4())
        assert mock_rec.receipt_confirmed_at is not None

    @pytest.mark.asyncio
    async def test_custom_confirmed_at_used(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        await confirm_receipt(session, tenant_id, uuid.uuid4(), confirmed_at=ts)
        assert mock_rec.receipt_confirmed_at == ts

    @pytest.mark.asyncio
    async def test_flushes(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await confirm_receipt(session, tenant_id, uuid.uuid4())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(AlignmentReceiptNotFoundError):
            await confirm_receipt(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_receipt_id(self, session, tenant_id):
        session.scalar.return_value = None
        rid = uuid.uuid4()
        with pytest.raises(AlignmentReceiptNotFoundError, match=str(rid)):
            await confirm_receipt(session, tenant_id, rid)


class TestConfirmAcknowledgment:
    @pytest.mark.asyncio
    async def test_sets_acknowledgment_confirmed_at(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        await confirm_acknowledgment(session, tenant_id, uuid.uuid4())
        assert mock_rec.acknowledgment_confirmed_at is not None

    @pytest.mark.asyncio
    async def test_custom_acknowledged_at_used(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        ts = datetime(2026, 6, 1, tzinfo=timezone.utc)
        await confirm_acknowledgment(session, tenant_id, uuid.uuid4(), acknowledged_at=ts)
        assert mock_rec.acknowledgment_confirmed_at == ts

    @pytest.mark.asyncio
    async def test_flushes(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await confirm_acknowledgment(session, tenant_id, uuid.uuid4())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(AlignmentReceiptNotFoundError):
            await confirm_acknowledgment(session, tenant_id, uuid.uuid4())


class TestListAlignment:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_alignment(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_records(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_alignment(session, tenant_id, project_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_stakeholder_filter_applied(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_alignment(session, tenant_id, project_id, stakeholder_id=uuid.uuid4())
        session.execute.assert_awaited_once()


class TestGetAlignmentGaps:
    @pytest.mark.asyncio
    async def test_returns_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_alignment_gaps(session, tenant_id, project_id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_empty_when_no_receipts(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_alignment_gaps(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_gap_result_objects(self, session, tenant_id, project_id):
        now = datetime.now(timezone.utc)
        r = MagicMock()
        r.id = uuid.uuid4()
        r.stakeholder_id = uuid.uuid4()
        r.event_type = "RiskIdentified"
        r.sent_at = now - timedelta(hours=30)
        r.receipt_confirmed_at = None
        r.acknowledgment_confirmed_at = None
        session.execute.return_value = _mock_rows([r])
        result = await get_alignment_gaps(session, tenant_id, project_id, now=now)
        assert all(isinstance(g, AlignmentGapResult) for g in result)


class TestGetAlignmentMap:
    @pytest.mark.asyncio
    async def test_returns_alignment_map_response(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_alignment_map(session, tenant_id, project_id)
        assert isinstance(result, AlignmentMapResponse)

    @pytest.mark.asyncio
    async def test_empty_map_zero_counts(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_alignment_map(session, tenant_id, project_id)
        assert result.total_receipts == 0
        assert result.unconfirmed_count == 0
        assert result.unacknowledged_count == 0

    @pytest.mark.asyncio
    async def test_total_receipts_counts_all(self, session, tenant_id, project_id):
        items = [MagicMock() for _ in range(3)]
        for m in items:
            m.receipt_confirmed_at = None
            m.acknowledgment_confirmed_at = None
            m.stakeholder_id = uuid.uuid4()
        session.execute.return_value = _mock_rows(items)
        result = await get_alignment_map(session, tenant_id, project_id)
        assert result.total_receipts == 3

    @pytest.mark.asyncio
    async def test_unconfirmed_count_correct(self, session, tenant_id, project_id):
        confirmed = MagicMock()
        confirmed.receipt_confirmed_at = datetime.now(timezone.utc)
        confirmed.acknowledgment_confirmed_at = None
        confirmed.stakeholder_id = uuid.uuid4()
        unconfirmed = MagicMock()
        unconfirmed.receipt_confirmed_at = None
        unconfirmed.acknowledgment_confirmed_at = None
        unconfirmed.stakeholder_id = uuid.uuid4()
        session.execute.return_value = _mock_rows([confirmed, unconfirmed])
        result = await get_alignment_map(session, tenant_id, project_id)
        assert result.unconfirmed_count == 1

    @pytest.mark.asyncio
    async def test_stakeholder_statuses_grouped(self, session, tenant_id, project_id):
        sid = uuid.uuid4()
        r1 = MagicMock()
        r1.stakeholder_id = sid
        r1.receipt_confirmed_at = datetime.now(timezone.utc)
        r1.acknowledgment_confirmed_at = None
        r2 = MagicMock()
        r2.stakeholder_id = sid
        r2.receipt_confirmed_at = None
        r2.acknowledgment_confirmed_at = None
        session.execute.return_value = _mock_rows([r1, r2])
        result = await get_alignment_map(session, tenant_id, project_id)
        assert len(result.stakeholders) == 1
        s = result.stakeholders[0]
        assert isinstance(s, StakeholderAlignmentStatus)
        assert s.total_events == 2
