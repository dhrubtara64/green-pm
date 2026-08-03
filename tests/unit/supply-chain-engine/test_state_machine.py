"""Tests for DispatchStateMachine — S7-02."""
import pytest

from app.dispatch.schemas import _DISPATCH_STAGES
from app.dispatch.state_machine import DispatchStateMachine, InvalidTransitionError


@pytest.fixture
def sm():
    return DispatchStateMachine()


class TestValidateTransition:
    def test_first_transition_valid(self, sm):
        sm.validate_transition("PO_RAISED", "VENDOR_CONFIRMED")

    def test_second_transition_valid(self, sm):
        sm.validate_transition("VENDOR_CONFIRMED", "MANUFACTURING")

    def test_all_sequential_transitions_valid(self, sm):
        for i in range(len(_DISPATCH_STAGES) - 1):
            sm.validate_transition(_DISPATCH_STAGES[i], _DISPATCH_STAGES[i + 1])

    def test_skipping_stage_raises(self, sm):
        with pytest.raises(InvalidTransitionError):
            sm.validate_transition("PO_RAISED", "MANUFACTURING")

    def test_backward_transition_raises(self, sm):
        with pytest.raises(InvalidTransitionError):
            sm.validate_transition("VENDOR_CONFIRMED", "PO_RAISED")

    def test_terminal_stage_raises(self, sm):
        with pytest.raises(InvalidTransitionError):
            sm.validate_transition("ACCEPTED", "PO_RAISED")

    def test_terminal_to_any_raises(self, sm):
        with pytest.raises(InvalidTransitionError):
            sm.validate_transition("ACCEPTED", "ACCEPTED")

    def test_unknown_current_stage_raises(self, sm):
        with pytest.raises(InvalidTransitionError):
            sm.validate_transition("NONEXISTENT", "VENDOR_CONFIRMED")

    def test_unknown_target_stage_raises(self, sm):
        with pytest.raises(InvalidTransitionError):
            sm.validate_transition("PO_RAISED", "NONEXISTENT")

    def test_error_message_contains_stages(self, sm):
        with pytest.raises(InvalidTransitionError, match="MANUFACTURING"):
            sm.validate_transition("PO_RAISED", "MANUFACTURING")

    def test_terminal_error_message_mentions_terminal(self, sm):
        with pytest.raises(InvalidTransitionError, match="terminal"):
            sm.validate_transition("ACCEPTED", "PO_RAISED")


class TestNextStage:
    def test_next_stage_from_first(self, sm):
        assert sm.next_stage("PO_RAISED") == "VENDOR_CONFIRMED"

    def test_next_stage_from_second(self, sm):
        assert sm.next_stage("VENDOR_CONFIRMED") == "MANUFACTURING"

    def test_next_stage_terminal_is_none(self, sm):
        assert sm.next_stage("ACCEPTED") is None

    def test_next_stage_all_sequential(self, sm):
        for i in range(len(_DISPATCH_STAGES) - 1):
            assert sm.next_stage(_DISPATCH_STAGES[i]) == _DISPATCH_STAGES[i + 1]

    def test_next_stage_unknown_is_none(self, sm):
        assert sm.next_stage("NONEXISTENT") is None


class TestIsTerminal:
    def test_accepted_is_terminal(self, sm):
        assert sm.is_terminal("ACCEPTED") is True

    def test_first_stage_not_terminal(self, sm):
        assert sm.is_terminal("PO_RAISED") is False

    def test_intermediate_stage_not_terminal(self, sm):
        assert sm.is_terminal("IN_TRANSIT") is False

    def test_all_non_terminal_stages(self, sm):
        for stage in _DISPATCH_STAGES[:-1]:
            assert sm.is_terminal(stage) is False


class TestStageIndex:
    def test_po_raised_index_zero(self, sm):
        assert sm.stage_index("PO_RAISED") == 0

    def test_accepted_index_nine(self, sm):
        assert sm.stage_index("ACCEPTED") == 9

    def test_all_indices_correct(self, sm):
        for i, stage in enumerate(_DISPATCH_STAGES):
            assert sm.stage_index(stage) == i

    def test_unknown_stage_raises(self, sm):
        with pytest.raises(ValueError):
            sm.stage_index("NONEXISTENT")
