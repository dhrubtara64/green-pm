"""Tests for Readiness Engine service layer — S10-01–S10-05."""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.readiness.service import (
    CriterionNotFoundError,
    GateNotFoundError,
    InvalidCriterionStatusError,
    InvalidGateTypeError,
    create_criterion,
    create_gate,
    get_blocking_items,
    get_gate,
    list_criteria,
    list_gates,
    recompute_gate_score,
    update_criterion_status,
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


# ---------------------------------------------------------------------------
# create_gate
# ---------------------------------------------------------------------------

class TestCreateGate:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_gate(session, tenant_id, project_id, "ENGINEERING")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await create_gate(session, tenant_id, project_id, "MATERIAL")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_status_is_not_started(self, session, tenant_id, project_id):
        gate = await create_gate(session, tenant_id, project_id, "QUALITY")
        assert gate.status == "NOT_STARTED"

    @pytest.mark.asyncio
    async def test_completion_zero(self, session, tenant_id, project_id):
        gate = await create_gate(session, tenant_id, project_id, "COD")
        assert gate.completion_percentage == 0.0

    @pytest.mark.asyncio
    async def test_stores_gate_type(self, session, tenant_id, project_id):
        gate = await create_gate(session, tenant_id, project_id, "COMMISSIONING")
        assert gate.gate_type == "COMMISSIONING"

    @pytest.mark.asyncio
    async def test_stores_project_id(self, session, tenant_id, project_id):
        gate = await create_gate(session, tenant_id, project_id, "CONSTRUCTION")
        assert gate.project_id == project_id

    @pytest.mark.asyncio
    async def test_stores_tenant_id(self, session, tenant_id, project_id):
        gate = await create_gate(session, tenant_id, project_id, "ENGINEERING")
        assert gate.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_invalid_gate_type_raises(self, session, tenant_id, project_id):
        with pytest.raises(InvalidGateTypeError):
            await create_gate(session, tenant_id, project_id, "BOGUS")


# ---------------------------------------------------------------------------
# get_gate
# ---------------------------------------------------------------------------

class TestGetGate:
    @pytest.mark.asyncio
    async def test_returns_gate_when_found(self, session, tenant_id):
        mock_gate = MagicMock()
        session.scalar.return_value = mock_gate
        result = await get_gate(session, tenant_id, uuid.uuid4())
        assert result is mock_gate

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(GateNotFoundError):
            await get_gate(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_gate_id(self, session, tenant_id):
        session.scalar.return_value = None
        gid = uuid.uuid4()
        with pytest.raises(GateNotFoundError, match=str(gid)):
            await get_gate(session, tenant_id, gid)


# ---------------------------------------------------------------------------
# list_gates
# ---------------------------------------------------------------------------

class TestListGates:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await list_gates(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_gates(self, session, tenant_id, project_id):
        gates = [MagicMock(), MagicMock()]
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = gates
        session.execute.return_value = mock_rows
        result = await list_gates(session, tenant_id, project_id)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# create_criterion
# ---------------------------------------------------------------------------

class TestCreateCriterion:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "ENGINEERING", "Approved drawings")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "MATERIAL", "Title")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_status_is_pending(self, session, tenant_id, project_id):
        c = await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "QUALITY", "QA sign-off")
        assert c.status == "PENDING"

    @pytest.mark.asyncio
    async def test_stores_title(self, session, tenant_id, project_id):
        c = await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "COD", "COD milestone")
        assert c.title == "COD milestone"

    @pytest.mark.asyncio
    async def test_stores_gate_type(self, session, tenant_id, project_id):
        c = await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "COMMISSIONING", "Test")
        assert c.gate_type == "COMMISSIONING"

    @pytest.mark.asyncio
    async def test_due_date_stored(self, session, tenant_id, project_id):
        d = date(2026, 12, 1)
        c = await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "ENGINEERING", "X", due_date=d)
        assert c.due_date == d

    @pytest.mark.asyncio
    async def test_responsible_party_stored(self, session, tenant_id, project_id):
        c = await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "CONSTRUCTION", "X", responsible_party="PM")
        assert c.responsible_party == "PM"

    @pytest.mark.asyncio
    async def test_description_optional_none(self, session, tenant_id, project_id):
        c = await create_criterion(session, tenant_id, uuid.uuid4(), project_id, "MATERIAL", "X")
        assert c.description is None


# ---------------------------------------------------------------------------
# update_criterion_status
# ---------------------------------------------------------------------------

class TestUpdateCriterionStatus:
    @pytest.mark.asyncio
    async def test_updates_to_met(self, session, tenant_id):
        crit = MagicMock()
        crit.status = "PENDING"
        session.scalar.return_value = crit
        await update_criterion_status(session, tenant_id, uuid.uuid4(), "MET")
        assert crit.status == "MET"

    @pytest.mark.asyncio
    async def test_updates_to_waived(self, session, tenant_id):
        crit = MagicMock()
        crit.status = "PENDING"
        session.scalar.return_value = crit
        await update_criterion_status(session, tenant_id, uuid.uuid4(), "WAIVED")
        assert crit.status == "WAIVED"

    @pytest.mark.asyncio
    async def test_invalid_status_raises(self, session, tenant_id):
        crit = MagicMock()
        session.scalar.return_value = crit
        with pytest.raises(InvalidCriterionStatusError):
            await update_criterion_status(session, tenant_id, uuid.uuid4(), "DONE")

    @pytest.mark.asyncio
    async def test_raises_criterion_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(CriterionNotFoundError):
            await update_criterion_status(session, tenant_id, uuid.uuid4(), "MET")

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id):
        crit = MagicMock()
        session.scalar.return_value = crit
        await update_criterion_status(session, tenant_id, uuid.uuid4(), "MET")
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# list_criteria
# ---------------------------------------------------------------------------

class TestListCriteria:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await list_criteria(session, tenant_id, uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_criteria(self, session, tenant_id):
        items = [MagicMock(), MagicMock(), MagicMock()]
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = items
        session.execute.return_value = mock_rows
        result = await list_criteria(session, tenant_id, uuid.uuid4())
        assert len(result) == 3


# ---------------------------------------------------------------------------
# recompute_gate_score
# ---------------------------------------------------------------------------

class TestRecomputeGateScore:
    def _make_gate(self, gate_type="ENGINEERING") -> MagicMock:
        g = MagicMock()
        g.gate_type = gate_type
        g.project_id = uuid.uuid4()
        g.status = "NOT_STARTED"
        g.completion_percentage = 0.0
        return g

    @pytest.mark.asyncio
    async def test_returns_readiness_score(self, session, tenant_id):
        gate = self._make_gate()
        session.scalar.return_value = gate
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        score = await recompute_gate_score(session, tenant_id, gate.id)
        assert score is not None

    @pytest.mark.asyncio
    async def test_stores_gate_type(self, session, tenant_id):
        gate = self._make_gate("MATERIAL")
        session.scalar.return_value = gate
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        score = await recompute_gate_score(session, tenant_id, gate.id)
        assert score.gate_type == "MATERIAL"

    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id):
        gate = self._make_gate()
        session.scalar.return_value = gate
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        await recompute_gate_score(session, tenant_id, gate.id)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id):
        gate = self._make_gate()
        session.scalar.return_value = gate
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        await recompute_gate_score(session, tenant_id, gate.id)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_gate_status(self, session, tenant_id):
        gate = self._make_gate("COMMISSIONING")
        session.scalar.return_value = gate
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        await recompute_gate_score(session, tenant_id, gate.id)
        # No criteria → READY
        assert gate.status == "READY"


# ---------------------------------------------------------------------------
# get_blocking_items
# ---------------------------------------------------------------------------

class TestGetBlockingItems:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none_overdue(self, session, tenant_id, project_id):
        future_criterion = MagicMock()
        future_criterion.status = "PENDING"
        future_criterion.due_date = date(2099, 1, 1)
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [future_criterion]
        session.execute.return_value = mock_rows

        result = await get_blocking_items(session, tenant_id, project_id, reference_date=date(2026, 8, 4))
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_overdue_items(self, session, tenant_id, project_id):
        past_criterion = MagicMock()
        past_criterion.status = "PENDING"
        past_criterion.due_date = date(2026, 1, 1)
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [past_criterion]
        session.execute.return_value = mock_rows

        result = await get_blocking_items(session, tenant_id, project_id, reference_date=date(2026, 8, 4))
        assert past_criterion in result
