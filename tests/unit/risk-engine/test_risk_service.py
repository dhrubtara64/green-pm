"""Tests for Risk Engine service layer — S9-01, S9-04, S9-05."""
import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.risk.service import (
    ClosedMitigationError,
    InvalidMitigationStatusError,
    InvalidRiskStatusError,
    RiskNotFoundError,
    create_assessment,
    create_mitigation,
    create_risk,
    get_risk,
    get_risk_register,
    list_risks,
    update_mitigation_effectiveness,
)
from app.risk.schemas import RiskRegisterEntry


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
# create_risk
# ---------------------------------------------------------------------------

class TestCreateRisk:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_risk(session, tenant_id, project_id, "Schedule", "Delay risk", 0.6, 0.7)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_session_flush(self, session, tenant_id, project_id):
        await create_risk(session, tenant_id, project_id, "Schedule", "Delay risk", 0.6, 0.7)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_risk_with_status_open(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "Cost", "Budget risk", 0.5, 0.8)
        assert risk.status == "OPEN"

    @pytest.mark.asyncio
    async def test_computes_risk_score(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "Cost", "Budget risk", 0.5, 0.8)
        assert risk.risk_score == pytest.approx(0.4, abs=0.001)

    @pytest.mark.asyncio
    async def test_risk_score_rounded_to_4dp(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "X", "Y", 0.3, 0.7)
        assert round(risk.risk_score, 4) == risk.risk_score

    @pytest.mark.asyncio
    async def test_stores_category(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "Regulatory", "Compliance risk", 0.4, 0.6)
        assert risk.category == "Regulatory"

    @pytest.mark.asyncio
    async def test_stores_project_id(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "X", "Y", 0.5, 0.5)
        assert risk.project_id == project_id

    @pytest.mark.asyncio
    async def test_stores_tenant_id(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "X", "Y", 0.5, 0.5)
        assert risk.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_probability_zero_gives_score_zero(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "X", "Y", 0.0, 0.9)
        assert risk.risk_score == 0.0

    @pytest.mark.asyncio
    async def test_impact_zero_gives_score_zero(self, session, tenant_id, project_id):
        risk = await create_risk(session, tenant_id, project_id, "X", "Y", 0.9, 0.0)
        assert risk.risk_score == 0.0


# ---------------------------------------------------------------------------
# get_risk
# ---------------------------------------------------------------------------

class TestGetRisk:
    @pytest.mark.asyncio
    async def test_returns_risk_when_found(self, session, tenant_id):
        mock_risk = MagicMock()
        session.scalar.return_value = mock_risk
        result = await get_risk(session, tenant_id, uuid.uuid4())
        assert result is mock_risk

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self, session, tenant_id):
        session.scalar.return_value = None
        rid = uuid.uuid4()
        with pytest.raises(RiskNotFoundError):
            await get_risk(session, tenant_id, rid)

    @pytest.mark.asyncio
    async def test_error_message_contains_risk_id(self, session, tenant_id):
        session.scalar.return_value = None
        rid = uuid.uuid4()
        with pytest.raises(RiskNotFoundError, match=str(rid)):
            await get_risk(session, tenant_id, rid)


# ---------------------------------------------------------------------------
# list_risks
# ---------------------------------------------------------------------------

class TestListRisks:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await list_risks(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_all_risks(self, session, tenant_id, project_id):
        risks = [MagicMock(), MagicMock()]
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = risks
        session.execute.return_value = mock_rows
        result = await list_risks(session, tenant_id, project_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_invalid_status_raises(self, session, tenant_id, project_id):
        with pytest.raises(InvalidRiskStatusError):
            await list_risks(session, tenant_id, project_id, status="UNKNOWN")

    @pytest.mark.asyncio
    async def test_none_status_no_filter(self, session, tenant_id, project_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        await list_risks(session, tenant_id, project_id, status=None)
        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_risk_register
# ---------------------------------------------------------------------------

class TestGetRiskRegister:
    @pytest.mark.asyncio
    async def test_returns_list_of_register_entries(self, session, tenant_id, project_id):
        mock_risk = MagicMock()
        mock_risk.id = uuid.uuid4()
        mock_risk.category = "Schedule"
        mock_risk.description = "Delay"
        mock_risk.risk_score = 0.36
        mock_risk.probability = 0.6
        mock_risk.impact = 0.6
        mock_risk.status = "OPEN"
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [mock_risk]
        session.execute.return_value = mock_rows
        result = await get_risk_register(session, tenant_id, project_id)
        assert len(result) == 1
        assert isinstance(result[0], RiskRegisterEntry)

    @pytest.mark.asyncio
    async def test_heat_map_x_is_probability(self, session, tenant_id, project_id):
        mock_risk = MagicMock()
        mock_risk.id = uuid.uuid4()
        mock_risk.category = "Cost"
        mock_risk.description = "Budget"
        mock_risk.risk_score = 0.2
        mock_risk.probability = 0.4
        mock_risk.impact = 0.5
        mock_risk.status = "OPEN"
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [mock_risk]
        session.execute.return_value = mock_rows
        result = await get_risk_register(session, tenant_id, project_id)
        assert result[0].heat_map.x == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_empty_register(self, session, tenant_id, project_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await get_risk_register(session, tenant_id, project_id)
        assert result == []


# ---------------------------------------------------------------------------
# create_assessment
# ---------------------------------------------------------------------------

class TestCreateAssessment:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Initial assessment", 100.0, 10.0, 500_000.0, 50_000.0, seed=42
        )
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_session_flush(self, session, tenant_id, project_id):
        await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Initial assessment", 100.0, 10.0, 500_000.0, 50_000.0, seed=42
        )
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stores_notes(self, session, tenant_id, project_id):
        assessment = await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Detailed notes", 100.0, 10.0, 500_000.0, 50_000.0, seed=0
        )
        assert assessment.notes == "Detailed notes"

    @pytest.mark.asyncio
    async def test_monte_carlo_result_is_dict(self, session, tenant_id, project_id):
        assessment = await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Notes", 100.0, 10.0, 500_000.0, 50_000.0, seed=0
        )
        assert isinstance(assessment.monte_carlo_result, dict)

    @pytest.mark.asyncio
    async def test_monte_carlo_result_has_schedule_key(self, session, tenant_id, project_id):
        assessment = await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Notes", 100.0, 10.0, 500_000.0, 50_000.0, seed=0
        )
        assert "schedule" in assessment.monte_carlo_result

    @pytest.mark.asyncio
    async def test_monte_carlo_result_has_cost_key(self, session, tenant_id, project_id):
        assessment = await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Notes", 100.0, 10.0, 500_000.0, 50_000.0, seed=0
        )
        assert "cost" in assessment.monte_carlo_result

    @pytest.mark.asyncio
    async def test_monte_carlo_result_schedule_has_p50(self, session, tenant_id, project_id):
        assessment = await create_assessment(
            session, tenant_id, uuid.uuid4(), project_id,
            "Notes", 100.0, 10.0, 500_000.0, 50_000.0, seed=0
        )
        assert "p50" in assessment.monte_carlo_result["schedule"]


# ---------------------------------------------------------------------------
# create_mitigation
# ---------------------------------------------------------------------------

class TestCreateMitigation:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_mitigation(session, tenant_id, uuid.uuid4(), project_id, "Engage backup supplier", "PM")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_is_open(self, session, tenant_id, project_id):
        m = await create_mitigation(session, tenant_id, uuid.uuid4(), project_id, "Action", "Owner")
        assert m.status == "OPEN"

    @pytest.mark.asyncio
    async def test_effectiveness_score_zero(self, session, tenant_id, project_id):
        m = await create_mitigation(session, tenant_id, uuid.uuid4(), project_id, "Action", "Owner")
        assert m.effectiveness_score == 0.0

    @pytest.mark.asyncio
    async def test_outcome_not_verified(self, session, tenant_id, project_id):
        m = await create_mitigation(session, tenant_id, uuid.uuid4(), project_id, "Action", "Owner")
        assert m.outcome_verified is False

    @pytest.mark.asyncio
    async def test_stores_action(self, session, tenant_id, project_id):
        m = await create_mitigation(session, tenant_id, uuid.uuid4(), project_id, "Engage supplier", "Owner")
        assert m.action == "Engage supplier"

    @pytest.mark.asyncio
    async def test_stores_owner(self, session, tenant_id, project_id):
        m = await create_mitigation(session, tenant_id, uuid.uuid4(), project_id, "Action", "Jane Doe")
        assert m.owner == "Jane Doe"


# ---------------------------------------------------------------------------
# update_mitigation_effectiveness
# ---------------------------------------------------------------------------

class TestUpdateMitigationEffectiveness:
    def _make_mitigation(self, status: str = "OPEN") -> MagicMock:
        m = MagicMock()
        m.status = status
        m.effectiveness_score = 0.0
        m.outcome_verified = False
        return m

    @pytest.mark.asyncio
    async def test_updates_effectiveness_score(self, session, tenant_id):
        mitigation = self._make_mitigation()
        session.scalar.return_value = mitigation
        await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.85)
        assert mitigation.effectiveness_score == 0.85

    @pytest.mark.asyncio
    async def test_marks_outcome_verified(self, session, tenant_id):
        mitigation = self._make_mitigation()
        session.scalar.return_value = mitigation
        await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.7)
        assert mitigation.outcome_verified is True

    @pytest.mark.asyncio
    async def test_updates_status_when_provided(self, session, tenant_id):
        mitigation = self._make_mitigation()
        session.scalar.return_value = mitigation
        await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.6, status="CLOSED")
        assert mitigation.status == "CLOSED"

    @pytest.mark.asyncio
    async def test_status_unchanged_when_not_provided(self, session, tenant_id):
        mitigation = self._make_mitigation(status="IN_PROGRESS")
        session.scalar.return_value = mitigation
        await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.5)
        assert mitigation.status == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(RiskNotFoundError):
            await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.5)

    @pytest.mark.asyncio
    async def test_raises_closed_error_for_closed_mitigation(self, session, tenant_id):
        mitigation = self._make_mitigation(status="CLOSED")
        session.scalar.return_value = mitigation
        with pytest.raises(ClosedMitigationError):
            await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.9)

    @pytest.mark.asyncio
    async def test_raises_invalid_status_error(self, session, tenant_id):
        mitigation = self._make_mitigation()
        session.scalar.return_value = mitigation
        with pytest.raises(InvalidMitigationStatusError):
            await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.5, status="BOGUS")

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id):
        mitigation = self._make_mitigation()
        session.scalar.return_value = mitigation
        await update_mitigation_effectiveness(session, tenant_id, uuid.uuid4(), 0.75)
        session.flush.assert_awaited_once()
