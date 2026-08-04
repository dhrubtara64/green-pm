"""Tests for Decision Engine 10-state lifecycle — S15-02."""
import pytest

from app.decision.lifecycle import (
    _DECISION_STATES,
    _TRANSITIONS,
    get_valid_transitions,
    is_terminal,
    is_valid_transition,
    required_approval_count,
    requires_approval_gate,
)


class TestDecisionStatesInLifecycle:
    def test_ten_states_defined(self):
        assert len(_DECISION_STATES) == 10

    def test_all_transition_keys_are_valid_states(self):
        for state in _TRANSITIONS:
            assert state in _DECISION_STATES

    def test_all_transition_targets_are_valid_states(self):
        for targets in _TRANSITIONS.values():
            for t in targets:
                assert t in _DECISION_STATES, f"{t!r} is not a valid state"


class TestIsValidTransition:
    def test_draft_to_submitted_valid(self):
        assert is_valid_transition("DRAFT", "SUBMITTED") is True

    def test_draft_to_archived_valid(self):
        assert is_valid_transition("DRAFT", "ARCHIVED") is True

    def test_draft_to_approved_invalid(self):
        assert is_valid_transition("DRAFT", "APPROVED") is False

    def test_submitted_to_under_review_valid(self):
        assert is_valid_transition("SUBMITTED", "UNDER_REVIEW") is True

    def test_submitted_to_draft_valid(self):
        assert is_valid_transition("SUBMITTED", "DRAFT") is True

    def test_submitted_to_approved_invalid(self):
        assert is_valid_transition("SUBMITTED", "APPROVED") is False

    def test_under_review_to_pending_approval_valid(self):
        assert is_valid_transition("UNDER_REVIEW", "PENDING_APPROVAL") is True

    def test_under_review_to_awaiting_input_valid(self):
        assert is_valid_transition("UNDER_REVIEW", "AWAITING_INPUT") is True

    def test_under_review_to_rejected_valid(self):
        assert is_valid_transition("UNDER_REVIEW", "REJECTED") is True

    def test_under_review_to_deferred_valid(self):
        assert is_valid_transition("UNDER_REVIEW", "DEFERRED") is True

    def test_awaiting_input_to_under_review_valid(self):
        assert is_valid_transition("AWAITING_INPUT", "UNDER_REVIEW") is True

    def test_awaiting_input_to_approved_invalid(self):
        assert is_valid_transition("AWAITING_INPUT", "APPROVED") is False

    def test_pending_approval_to_approved_valid(self):
        assert is_valid_transition("PENDING_APPROVAL", "APPROVED") is True

    def test_pending_approval_to_rejected_valid(self):
        assert is_valid_transition("PENDING_APPROVAL", "REJECTED") is True

    def test_pending_approval_to_deferred_valid(self):
        assert is_valid_transition("PENDING_APPROVAL", "DEFERRED") is True

    def test_approved_to_superseded_valid(self):
        assert is_valid_transition("APPROVED", "SUPERSEDED") is True

    def test_approved_to_archived_valid(self):
        assert is_valid_transition("APPROVED", "ARCHIVED") is True

    def test_approved_to_draft_invalid(self):
        assert is_valid_transition("APPROVED", "DRAFT") is False

    def test_rejected_to_archived_valid(self):
        assert is_valid_transition("REJECTED", "ARCHIVED") is True

    def test_rejected_to_draft_valid(self):
        assert is_valid_transition("REJECTED", "DRAFT") is True

    def test_deferred_to_under_review_valid(self):
        assert is_valid_transition("DEFERRED", "UNDER_REVIEW") is True

    def test_superseded_to_archived_valid(self):
        assert is_valid_transition("SUPERSEDED", "ARCHIVED") is True

    def test_superseded_to_draft_invalid(self):
        assert is_valid_transition("SUPERSEDED", "DRAFT") is False

    def test_archived_has_no_valid_transitions(self):
        for state in _DECISION_STATES:
            assert is_valid_transition("ARCHIVED", state) is False

    def test_unknown_from_state_returns_false(self):
        assert is_valid_transition("BOGUS", "DRAFT") is False

    def test_same_state_not_valid(self):
        assert is_valid_transition("DRAFT", "DRAFT") is False


class TestGetValidTransitions:
    def test_draft_returns_frozenset(self):
        result = get_valid_transitions("DRAFT")
        assert isinstance(result, frozenset)

    def test_draft_has_two_targets(self):
        result = get_valid_transitions("DRAFT")
        assert len(result) == 2

    def test_archived_returns_empty_frozenset(self):
        assert get_valid_transitions("ARCHIVED") == frozenset()

    def test_unknown_state_returns_empty_frozenset(self):
        assert get_valid_transitions("NONEXISTENT") == frozenset()

    def test_pending_approval_returns_three_targets(self):
        result = get_valid_transitions("PENDING_APPROVAL")
        assert len(result) == 3


class TestIsTerminal:
    def test_archived_is_terminal(self):
        assert is_terminal("ARCHIVED") is True

    def test_draft_not_terminal(self):
        assert is_terminal("DRAFT") is False

    def test_approved_not_terminal(self):
        assert is_terminal("APPROVED") is False

    def test_superseded_not_terminal(self):
        assert is_terminal("SUPERSEDED") is False

    def test_all_non_archived_not_terminal(self):
        for state in _DECISION_STATES - {"ARCHIVED"}:
            assert is_terminal(state) is False


class TestRequiresApprovalGate:
    def test_approved_requires_gate(self):
        assert requires_approval_gate("APPROVED") is True

    def test_draft_does_not_require_gate(self):
        assert requires_approval_gate("DRAFT") is False

    def test_submitted_does_not_require_gate(self):
        assert requires_approval_gate("SUBMITTED") is False

    def test_pending_approval_does_not_require_gate(self):
        assert requires_approval_gate("PENDING_APPROVAL") is False


class TestRequiredApprovalCount:
    def test_high_impact_approval_required_returns_two(self):
        assert required_approval_count("HIGH", approval_required=True) == 2

    def test_medium_impact_approval_required_returns_one(self):
        assert required_approval_count("MEDIUM", approval_required=True) == 1

    def test_low_impact_approval_required_returns_one(self):
        assert required_approval_count("LOW", approval_required=True) == 1

    def test_high_impact_approval_not_required_returns_zero(self):
        assert required_approval_count("HIGH", approval_required=False) == 0

    def test_medium_impact_approval_not_required_returns_zero(self):
        assert required_approval_count("MEDIUM", approval_required=False) == 0
