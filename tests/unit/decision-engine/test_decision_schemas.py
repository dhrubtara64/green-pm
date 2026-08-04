"""Tests for Decision Engine schemas — S15-01, S15-02, S15-03, S15-04."""
import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.decision.schemas import (
    _DECISION_STATES,
    _IMPACT_LEVELS,
    _PRIORITY_LEVELS,
    DecisionApprovalCreate,
    DecisionApprovalResponse,
    DecisionCreate,
    DecisionOptionCreate,
    DecisionOptionResponse,
    DecisionQuery,
    DecisionResponse,
)


class TestDecisionStatesConstant:
    def test_is_frozenset(self):
        assert isinstance(_DECISION_STATES, frozenset)

    def test_has_ten_states(self):
        assert len(_DECISION_STATES) == 10

    def test_draft_present(self):
        assert "DRAFT" in _DECISION_STATES

    def test_submitted_present(self):
        assert "SUBMITTED" in _DECISION_STATES

    def test_under_review_present(self):
        assert "UNDER_REVIEW" in _DECISION_STATES

    def test_awaiting_input_present(self):
        assert "AWAITING_INPUT" in _DECISION_STATES

    def test_pending_approval_present(self):
        assert "PENDING_APPROVAL" in _DECISION_STATES

    def test_approved_present(self):
        assert "APPROVED" in _DECISION_STATES

    def test_rejected_present(self):
        assert "REJECTED" in _DECISION_STATES

    def test_deferred_present(self):
        assert "DEFERRED" in _DECISION_STATES

    def test_superseded_present(self):
        assert "SUPERSEDED" in _DECISION_STATES

    def test_archived_present(self):
        assert "ARCHIVED" in _DECISION_STATES


class TestPriorityLevelsConstant:
    def test_is_frozenset(self):
        assert isinstance(_PRIORITY_LEVELS, frozenset)

    def test_has_four_levels(self):
        assert len(_PRIORITY_LEVELS) == 4

    def test_contains_low(self):
        assert "LOW" in _PRIORITY_LEVELS

    def test_contains_medium(self):
        assert "MEDIUM" in _PRIORITY_LEVELS

    def test_contains_high(self):
        assert "HIGH" in _PRIORITY_LEVELS

    def test_contains_critical(self):
        assert "CRITICAL" in _PRIORITY_LEVELS


class TestImpactLevelsConstant:
    def test_is_frozenset(self):
        assert isinstance(_IMPACT_LEVELS, frozenset)

    def test_has_three_levels(self):
        assert len(_IMPACT_LEVELS) == 3


class TestDecisionQuery:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        q = DecisionQuery(project_id=pid)
        assert q.project_id == pid

    def test_lifecycle_status_defaults_none(self):
        q = DecisionQuery(project_id=uuid.uuid4())
        assert q.lifecycle_status is None

    def test_valid_lifecycle_status_accepted(self):
        q = DecisionQuery(project_id=uuid.uuid4(), lifecycle_status="DRAFT")
        assert q.lifecycle_status == "DRAFT"

    def test_all_ten_states_valid(self):
        pid = uuid.uuid4()
        for state in _DECISION_STATES:
            q = DecisionQuery(project_id=pid, lifecycle_status=state)
            assert q.lifecycle_status == state

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            DecisionQuery(project_id=uuid.uuid4(), lifecycle_status="INVALID")

    def test_is_frozen(self):
        q = DecisionQuery(project_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            q.project_id = uuid.uuid4()  # type: ignore[misc]


class TestDecisionCreate:
    def _pid(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_stores_project_id(self):
        pid = self._pid()
        c = DecisionCreate(project_id=pid, title="Build new bridge")
        assert c.project_id == pid

    def test_stores_title(self):
        c = DecisionCreate(project_id=self._pid(), title="Approve contractor")
        assert c.title == "Approve contractor"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            DecisionCreate(project_id=self._pid(), title="")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            DecisionCreate(project_id=self._pid(), title="   ")

    def test_description_defaults_none(self):
        c = DecisionCreate(project_id=self._pid(), title="t")
        assert c.description is None

    def test_priority_defaults_medium(self):
        c = DecisionCreate(project_id=self._pid(), title="t")
        assert c.priority == "MEDIUM"

    def test_impact_level_defaults_low(self):
        c = DecisionCreate(project_id=self._pid(), title="t")
        assert c.impact_level == "LOW"

    def test_approval_required_defaults_false(self):
        c = DecisionCreate(project_id=self._pid(), title="t")
        assert c.approval_required is False

    def test_valid_priority_accepted(self):
        c = DecisionCreate(project_id=self._pid(), title="t", priority="HIGH")
        assert c.priority == "HIGH"

    def test_invalid_priority_raises(self):
        with pytest.raises(ValidationError):
            DecisionCreate(project_id=self._pid(), title="t", priority="EXTREME")

    def test_valid_impact_level_accepted(self):
        c = DecisionCreate(project_id=self._pid(), title="t", impact_level="HIGH")
        assert c.impact_level == "HIGH"

    def test_invalid_impact_level_raises(self):
        with pytest.raises(ValidationError):
            DecisionCreate(project_id=self._pid(), title="t", impact_level="CATASTROPHIC")

    def test_approval_required_true(self):
        c = DecisionCreate(project_id=self._pid(), title="t", approval_required=True)
        assert c.approval_required is True


class TestDecisionResponse:
    def test_from_attributes_enabled(self):
        assert DecisionResponse.model_config.get("from_attributes") is True

    def test_historical_context_defaults_empty_list(self):
        r = DecisionResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            title="t",
            lifecycle_status="DRAFT",
            priority="MEDIUM",
            impact_level="LOW",
            approval_required=False,
            approval_count=0,
        )
        assert r.historical_context == []

    def test_optional_timestamps_default_none(self):
        r = DecisionResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            title="t",
            lifecycle_status="DRAFT",
            priority="MEDIUM",
            impact_level="LOW",
            approval_required=False,
            approval_count=0,
        )
        assert r.created_at is None

    def test_stores_approval_count(self):
        r = DecisionResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            title="t",
            lifecycle_status="APPROVED",
            priority="HIGH",
            impact_level="HIGH",
            approval_required=True,
            approval_count=2,
        )
        assert r.approval_count == 2


class TestDecisionOptionCreate:
    def test_stores_option_text(self):
        c = DecisionOptionCreate(decision_id=uuid.uuid4(), option_text="Option A: proceed")
        assert c.option_text == "Option A: proceed"

    def test_empty_option_text_raises(self):
        with pytest.raises(ValidationError):
            DecisionOptionCreate(decision_id=uuid.uuid4(), option_text="")

    def test_pros_defaults_none(self):
        c = DecisionOptionCreate(decision_id=uuid.uuid4(), option_text="A")
        assert c.pros is None

    def test_cons_defaults_none(self):
        c = DecisionOptionCreate(decision_id=uuid.uuid4(), option_text="A")
        assert c.cons is None


class TestDecisionApprovalCreate:
    def test_stores_decision_id(self):
        did = uuid.uuid4()
        c = DecisionApprovalCreate(decision_id=did, approver_id=uuid.uuid4(), approved=True)
        assert c.decision_id == did

    def test_stores_approved_true(self):
        c = DecisionApprovalCreate(
            decision_id=uuid.uuid4(), approver_id=uuid.uuid4(), approved=True
        )
        assert c.approved is True

    def test_stores_approved_false(self):
        c = DecisionApprovalCreate(
            decision_id=uuid.uuid4(), approver_id=uuid.uuid4(), approved=False
        )
        assert c.approved is False

    def test_comment_defaults_none(self):
        c = DecisionApprovalCreate(
            decision_id=uuid.uuid4(), approver_id=uuid.uuid4(), approved=True
        )
        assert c.comment is None
