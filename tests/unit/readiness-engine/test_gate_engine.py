"""Tests for gate computation logic — S10-02, S10-04."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.readiness.gate_engine import (
    compute_gate_status,
    identify_blocking_items,
)
from app.readiness.schemas import GateComputationResult

# Reference date used throughout to make tests deterministic
_TODAY = date(2026, 8, 4)
_YESTERDAY = date(2026, 8, 3)
_TOMORROW = date(2026, 8, 5)
_LAST_MONTH = date(2026, 7, 1)


def _criterion(status: str, due_date=None) -> MagicMock:
    c = MagicMock()
    c.status = status
    c.due_date = due_date
    return c


class TestComputeGateStatusNoCriteria:
    def test_returns_gate_computation_result(self):
        r = compute_gate_status("ENGINEERING", [], reference_date=_TODAY)
        assert isinstance(r, GateComputationResult)

    def test_no_criteria_returns_ready(self):
        r = compute_gate_status("MATERIAL", [], reference_date=_TODAY)
        assert r.status == "READY"

    def test_no_criteria_completion_is_100(self):
        r = compute_gate_status("CONSTRUCTION", [], reference_date=_TODAY)
        assert r.completion_percentage == 100.0

    def test_no_criteria_totals_are_zero(self):
        r = compute_gate_status("QUALITY", [], reference_date=_TODAY)
        assert r.total_criteria == 0
        assert r.met_criteria == 0
        assert r.waived_criteria == 0

    def test_invalid_gate_type_raises(self):
        with pytest.raises(ValueError, match="gate_type"):
            compute_gate_status("BOGUS", [], reference_date=_TODAY)


class TestComputeGateStatusAllPending:
    def test_all_pending_no_overdue_is_not_started(self):
        criteria = [_criterion("PENDING", _TOMORROW) for _ in range(3)]
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.status == "NOT_STARTED"

    def test_all_pending_no_due_date_is_not_started(self):
        criteria = [_criterion("PENDING", None) for _ in range(2)]
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.status == "NOT_STARTED"

    def test_all_pending_overdue_is_blocked(self):
        criteria = [_criterion("PENDING", _YESTERDAY)]
        r = compute_gate_status("COMMISSIONING", criteria, reference_date=_TODAY)
        assert r.status == "BLOCKED"

    def test_completion_zero_when_all_pending(self):
        criteria = [_criterion("PENDING", None) for _ in range(4)]
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.completion_percentage == 0.0

    def test_pending_count_correct(self):
        criteria = [_criterion("PENDING", None) for _ in range(5)]
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.pending_criteria == 5


class TestComputeGateStatusMixedCriteria:
    def test_some_met_no_overdue_is_in_progress(self):
        criteria = [_criterion("MET"), _criterion("PENDING", _TOMORROW)]
        r = compute_gate_status("MATERIAL", criteria, reference_date=_TODAY)
        assert r.status == "IN_PROGRESS"

    def test_some_waived_no_overdue_is_in_progress(self):
        criteria = [_criterion("WAIVED"), _criterion("PENDING", None)]
        r = compute_gate_status("QUALITY", criteria, reference_date=_TODAY)
        assert r.status == "IN_PROGRESS"

    def test_overdue_pending_overrides_to_blocked(self):
        criteria = [_criterion("MET"), _criterion("PENDING", _YESTERDAY)]
        r = compute_gate_status("CONSTRUCTION", criteria, reference_date=_TODAY)
        assert r.status == "BLOCKED"

    def test_completion_percentage_computed(self):
        # 3 MET + 1 PENDING = 75%
        criteria = [_criterion("MET")] * 3 + [_criterion("PENDING", None)]
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.completion_percentage == 75.0

    def test_met_and_waived_both_count(self):
        # 2 MET + 2 WAIVED + 1 PENDING = 80%
        criteria = [_criterion("MET")] * 2 + [_criterion("WAIVED")] * 2 + [_criterion("PENDING", None)]
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.completion_percentage == 80.0

    def test_met_count_correct(self):
        criteria = [_criterion("MET")] * 4 + [_criterion("PENDING", None)] * 2
        r = compute_gate_status("MATERIAL", criteria, reference_date=_TODAY)
        assert r.met_criteria == 4

    def test_waived_count_correct(self):
        criteria = [_criterion("WAIVED")] * 3 + [_criterion("PENDING", None)]
        r = compute_gate_status("COD", criteria, reference_date=_TODAY)
        assert r.waived_criteria == 3

    def test_total_count_correct(self):
        criteria = [_criterion("MET")] * 2 + [_criterion("PENDING", None)] * 3
        r = compute_gate_status("QUALITY", criteria, reference_date=_TODAY)
        assert r.total_criteria == 5


class TestComputeGateStatusAllDone:
    def test_all_met_is_ready(self):
        criteria = [_criterion("MET") for _ in range(5)]
        r = compute_gate_status("COMMISSIONING", criteria, reference_date=_TODAY)
        assert r.status == "READY"

    def test_all_waived_is_ready(self):
        criteria = [_criterion("WAIVED") for _ in range(3)]
        r = compute_gate_status("COD", criteria, reference_date=_TODAY)
        assert r.status == "READY"

    def test_mixed_met_waived_is_ready(self):
        criteria = [_criterion("MET")] * 3 + [_criterion("WAIVED")] * 2
        r = compute_gate_status("ENGINEERING", criteria, reference_date=_TODAY)
        assert r.status == "READY"

    def test_all_done_completion_is_100(self):
        criteria = [_criterion("MET")] * 5
        r = compute_gate_status("MATERIAL", criteria, reference_date=_TODAY)
        assert r.completion_percentage == 100.0


class TestIdentifyBlockingItems:
    def test_overdue_pending_returned(self):
        c = _criterion("PENDING", _YESTERDAY)
        result = identify_blocking_items([c], reference_date=_TODAY)
        assert c in result

    def test_future_pending_not_returned(self):
        c = _criterion("PENDING", _TOMORROW)
        result = identify_blocking_items([c], reference_date=_TODAY)
        assert result == []

    def test_no_due_date_not_returned(self):
        c = _criterion("PENDING", None)
        result = identify_blocking_items([c], reference_date=_TODAY)
        assert result == []

    def test_met_not_returned_even_if_past(self):
        c = _criterion("MET", _YESTERDAY)
        result = identify_blocking_items([c], reference_date=_TODAY)
        assert result == []

    def test_waived_not_returned(self):
        c = _criterion("WAIVED", _LAST_MONTH)
        result = identify_blocking_items([c], reference_date=_TODAY)
        assert result == []

    def test_empty_list_returns_empty(self):
        assert identify_blocking_items([], reference_date=_TODAY) == []

    def test_multiple_blocking_items_all_returned(self):
        overdue = [_criterion("PENDING", _LAST_MONTH) for _ in range(3)]
        ok = [_criterion("PENDING", _TOMORROW)]
        result = identify_blocking_items(overdue + ok, reference_date=_TODAY)
        assert len(result) == 3
