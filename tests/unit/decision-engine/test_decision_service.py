"""Tests for Decision Engine service layer — S15-02, S15-03, S15-04, S15-05."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.decision.schemas import DecisionApprovalCreate, DecisionCreate
from app.decision.service import (
    DecisionNotFoundError,
    InsufficientApprovalsError,
    InvalidTransitionError,
    advance_decision_state,
    create_decision,
    get_decision,
    list_decisions,
    submit_approval,
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


def _create(project_id: uuid.UUID, **kw) -> DecisionCreate:
    return DecisionCreate(
        project_id=project_id,
        title=kw.get("title", "Approve scope change"),
        priority=kw.get("priority", "MEDIUM"),
        impact_level=kw.get("impact_level", "LOW"),
        approval_required=kw.get("approval_required", False),
    )


def _mock_decision(**kw) -> MagicMock:
    d = MagicMock()
    d.id = kw.get("id", uuid.uuid4())
    d.lifecycle_status = kw.get("lifecycle_status", "PENDING_APPROVAL")
    d.impact_level = kw.get("impact_level", "LOW")
    d.approval_required = kw.get("approval_required", True)
    d.approval_count = kw.get("approval_count", 0)
    return d


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestCreateDecision:
    @pytest.mark.asyncio
    async def test_calls_add(self, session, tenant_id, project_id):
        await create_decision(session, tenant_id, _create(project_id))
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await create_decision(session, tenant_id, _create(project_id))
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert isinstance(rec.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_lifecycle_status_is_draft(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert rec.lifecycle_status == "DRAFT"

    @pytest.mark.asyncio
    async def test_approval_count_is_zero(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert rec.approval_count == 0

    @pytest.mark.asyncio
    async def test_title_stored(self, session, tenant_id, project_id):
        rec = await create_decision(
            session, tenant_id, _create(project_id, title="Approve new vendor")
        )
        assert rec.title == "Approve new vendor"

    @pytest.mark.asyncio
    async def test_tenant_id_stored(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert rec.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_project_id_stored(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert rec.project_id == project_id

    @pytest.mark.asyncio
    async def test_created_at_set(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert rec.created_at is not None

    @pytest.mark.asyncio
    async def test_historical_context_stored_when_provided(self, session, tenant_id, project_id):
        ctx = [{"pattern_name": "delay_risk", "confidence_score": 0.85}]
        rec = await create_decision(session, tenant_id, _create(project_id), historical_context=ctx)
        assert rec.historical_context == ctx

    @pytest.mark.asyncio
    async def test_historical_context_none_when_not_provided(self, session, tenant_id, project_id):
        rec = await create_decision(session, tenant_id, _create(project_id))
        assert rec.historical_context is None


class TestAdvanceDecisionState:
    @pytest.mark.asyncio
    async def test_valid_transition_sets_new_state(self, session, tenant_id):
        d = _mock_decision(lifecycle_status="SUBMITTED")
        session.scalar.return_value = d
        result = await advance_decision_state(session, tenant_id, d.id, "UNDER_REVIEW")
        assert result.lifecycle_status == "UNDER_REVIEW"

    @pytest.mark.asyncio
    async def test_valid_transition_flushes(self, session, tenant_id):
        d = _mock_decision(lifecycle_status="DRAFT")
        session.scalar.return_value = d
        await advance_decision_state(session, tenant_id, d.id, "SUBMITTED")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self, session, tenant_id):
        d = _mock_decision(lifecycle_status="DRAFT")
        session.scalar.return_value = d
        with pytest.raises(InvalidTransitionError):
            await advance_decision_state(session, tenant_id, d.id, "APPROVED")

    @pytest.mark.asyncio
    async def test_error_message_contains_from_state(self, session, tenant_id):
        d = _mock_decision(lifecycle_status="DRAFT")
        session.scalar.return_value = d
        with pytest.raises(InvalidTransitionError, match="DRAFT"):
            await advance_decision_state(session, tenant_id, d.id, "APPROVED")

    @pytest.mark.asyncio
    async def test_not_found_raises_decision_not_found_error(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(DecisionNotFoundError):
            await advance_decision_state(session, tenant_id, uuid.uuid4(), "SUBMITTED")

    @pytest.mark.asyncio
    async def test_approved_without_approval_required_succeeds(self, session, tenant_id):
        d = _mock_decision(
            lifecycle_status="PENDING_APPROVAL",
            approval_required=False,
            approval_count=0,
        )
        session.scalar.return_value = d
        result = await advance_decision_state(session, tenant_id, d.id, "APPROVED")
        assert result.lifecycle_status == "APPROVED"

    @pytest.mark.asyncio
    async def test_approved_with_sufficient_approvals_succeeds(self, session, tenant_id):
        d = _mock_decision(
            lifecycle_status="PENDING_APPROVAL",
            approval_required=True,
            impact_level="LOW",
            approval_count=1,
        )
        session.scalar.return_value = d
        result = await advance_decision_state(session, tenant_id, d.id, "APPROVED")
        assert result.lifecycle_status == "APPROVED"

    @pytest.mark.asyncio
    async def test_approved_high_impact_requires_two_approvals(self, session, tenant_id):
        d = _mock_decision(
            lifecycle_status="PENDING_APPROVAL",
            approval_required=True,
            impact_level="HIGH",
            approval_count=1,
        )
        session.scalar.return_value = d
        with pytest.raises(InsufficientApprovalsError):
            await advance_decision_state(session, tenant_id, d.id, "APPROVED")

    @pytest.mark.asyncio
    async def test_approved_high_impact_with_two_approvals_succeeds(self, session, tenant_id):
        d = _mock_decision(
            lifecycle_status="PENDING_APPROVAL",
            approval_required=True,
            impact_level="HIGH",
            approval_count=2,
        )
        session.scalar.return_value = d
        result = await advance_decision_state(session, tenant_id, d.id, "APPROVED")
        assert result.lifecycle_status == "APPROVED"

    @pytest.mark.asyncio
    async def test_approved_approval_required_no_approvals_raises(self, session, tenant_id):
        d = _mock_decision(
            lifecycle_status="PENDING_APPROVAL",
            approval_required=True,
            impact_level="LOW",
            approval_count=0,
        )
        session.scalar.return_value = d
        with pytest.raises(InsufficientApprovalsError):
            await advance_decision_state(session, tenant_id, d.id, "APPROVED")


class TestSubmitApproval:
    def _approval_create(self, decision_id: uuid.UUID, approved: bool = True) -> DecisionApprovalCreate:
        return DecisionApprovalCreate(
            decision_id=decision_id,
            approver_id=uuid.uuid4(),
            approved=approved,
        )

    @pytest.mark.asyncio
    async def test_adds_approval_record(self, session, tenant_id):
        d = _mock_decision()
        session.scalar.return_value = d
        await submit_approval(session, tenant_id, self._approval_create(d.id))
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flushes(self, session, tenant_id):
        d = _mock_decision()
        session.scalar.return_value = d
        await submit_approval(session, tenant_id, self._approval_create(d.id))
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approval_true_increments_count(self, session, tenant_id):
        d = _mock_decision(approval_count=0)
        session.scalar.return_value = d
        await submit_approval(session, tenant_id, self._approval_create(d.id, approved=True))
        assert d.approval_count == 1

    @pytest.mark.asyncio
    async def test_approval_false_does_not_increment_count(self, session, tenant_id):
        d = _mock_decision(approval_count=0)
        session.scalar.return_value = d
        await submit_approval(session, tenant_id, self._approval_create(d.id, approved=False))
        assert d.approval_count == 0

    @pytest.mark.asyncio
    async def test_returns_decision(self, session, tenant_id):
        d = _mock_decision()
        session.scalar.return_value = d
        result = await submit_approval(session, tenant_id, self._approval_create(d.id))
        assert result is d

    @pytest.mark.asyncio
    async def test_not_found_raises(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(DecisionNotFoundError):
            await submit_approval(
                session, tenant_id,
                DecisionApprovalCreate(
                    decision_id=uuid.uuid4(), approver_id=uuid.uuid4(), approved=True
                ),
            )


class TestListDecisions:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_decisions(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_records(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_decisions(session, tenant_id, project_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_status_filter_applied(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_decisions(session, tenant_id, project_id, lifecycle_status="APPROVED")
        session.execute.assert_awaited_once()


class TestGetDecision:
    @pytest.mark.asyncio
    async def test_returns_record_when_found(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_decision(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(DecisionNotFoundError):
            await get_decision(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_decision_id(self, session, tenant_id):
        session.scalar.return_value = None
        did = uuid.uuid4()
        with pytest.raises(DecisionNotFoundError, match=str(did)):
            await get_decision(session, tenant_id, did)
