"""Tests for Coordination Engine domain and API schemas — S12-01, S12-03, S12-04."""
import uuid
from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from app.coordination.schemas import (
    CoordinationClosureResponse,
    CoordinationItemCreate,
    CoordinationItemResponse,
    CoordinationSummaryResponse,
    CoordinationTransition,
    StatusTransitionRequest,
    _COORDINATION_STATUSES,
    _TERMINAL_STATUSES,
    _VALID_TRANSITIONS,
)


class TestCoordinationStatusesConstant:
    def test_is_frozenset(self):
        assert isinstance(_COORDINATION_STATUSES, frozenset)

    def test_has_five_values(self):
        assert len(_COORDINATION_STATUSES) == 5

    def test_open_present(self):
        assert "OPEN" in _COORDINATION_STATUSES

    def test_acknowledged_present(self):
        assert "ACKNOWLEDGED" in _COORDINATION_STATUSES

    def test_executing_present(self):
        assert "EXECUTING" in _COORDINATION_STATUSES

    def test_verified_present(self):
        assert "VERIFIED" in _COORDINATION_STATUSES

    def test_closed_present(self):
        assert "CLOSED" in _COORDINATION_STATUSES


class TestTerminalStatusesConstant:
    def test_is_frozenset(self):
        assert isinstance(_TERMINAL_STATUSES, frozenset)

    def test_verified_is_terminal(self):
        assert "VERIFIED" in _TERMINAL_STATUSES

    def test_closed_is_terminal(self):
        assert "CLOSED" in _TERMINAL_STATUSES

    def test_open_not_terminal(self):
        assert "OPEN" not in _TERMINAL_STATUSES

    def test_acknowledged_not_terminal(self):
        assert "ACKNOWLEDGED" not in _TERMINAL_STATUSES

    def test_executing_not_terminal(self):
        assert "EXECUTING" not in _TERMINAL_STATUSES


class TestValidTransitionsConstant:
    def test_is_dict(self):
        assert isinstance(_VALID_TRANSITIONS, dict)

    def test_open_to_acknowledged(self):
        assert _VALID_TRANSITIONS["OPEN"] == "ACKNOWLEDGED"

    def test_acknowledged_to_executing(self):
        assert _VALID_TRANSITIONS["ACKNOWLEDGED"] == "EXECUTING"

    def test_executing_to_verified(self):
        assert _VALID_TRANSITIONS["EXECUTING"] == "VERIFIED"

    def test_verified_to_closed(self):
        assert _VALID_TRANSITIONS["VERIFIED"] == "CLOSED"

    def test_has_four_entries(self):
        assert len(_VALID_TRANSITIONS) == 4


class TestCoordinationTransition:
    def _make(self, **overrides) -> CoordinationTransition:
        base = dict(
            item_id=uuid.uuid4(),
            from_status="OPEN",
            to_status="ACKNOWLEDGED",
        )
        return CoordinationTransition(**{**base, **overrides})

    def test_stores_item_id(self):
        sid = uuid.uuid4()
        t = self._make(item_id=sid)
        assert t.item_id == sid

    def test_stores_from_status(self):
        assert self._make().from_status == "OPEN"

    def test_stores_to_status(self):
        assert self._make().to_status == "ACKNOWLEDGED"

    def test_is_frozen(self):
        t = self._make()
        with pytest.raises(FrozenInstanceError):
            t.from_status = "CLOSED"  # type: ignore[misc]

    def test_invalid_from_status_raises(self):
        with pytest.raises(ValueError, match="from_status"):
            self._make(from_status="BOGUS")

    def test_invalid_to_status_raises(self):
        with pytest.raises(ValueError, match="to_status"):
            self._make(to_status="BOGUS")

    def test_invalid_transition_raises(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            self._make(from_status="OPEN", to_status="CLOSED")

    def test_skip_transition_raises(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            self._make(from_status="OPEN", to_status="EXECUTING")

    def test_all_valid_sequential_transitions(self):
        pairs = [
            ("OPEN", "ACKNOWLEDGED"),
            ("ACKNOWLEDGED", "EXECUTING"),
            ("EXECUTING", "VERIFIED"),
            ("VERIFIED", "CLOSED"),
        ]
        for frm, to in pairs:
            t = self._make(from_status=frm, to_status=to)
            assert t.from_status == frm
            assert t.to_status == to

    def test_reverse_transition_raises(self):
        with pytest.raises(ValueError):
            self._make(from_status="ACKNOWLEDGED", to_status="OPEN")

    def test_same_status_raises(self):
        with pytest.raises(ValueError):
            self._make(from_status="OPEN", to_status="OPEN")


class TestCoordinationItemCreate:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        c = CoordinationItemCreate(project_id=pid, title="X")
        assert c.project_id == pid

    def test_stores_title(self):
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="Risk coordination")
        assert c.title == "Risk coordination"

    def test_description_optional(self):
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="X")
        assert c.description is None

    def test_assignee_id_optional(self):
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="X")
        assert c.assignee_id is None

    def test_due_date_optional(self):
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="X")
        assert c.due_date is None

    def test_source_event_id_optional(self):
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="X")
        assert c.source_event_id is None

    def test_source_event_id_stored(self):
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="X",
                                   source_event_id="evt-abc-123")
        assert c.source_event_id == "evt-abc-123"

    def test_due_date_stored(self):
        d = date(2026, 9, 1)
        c = CoordinationItemCreate(project_id=uuid.uuid4(), title="X", due_date=d)
        assert c.due_date == d


class TestCoordinationItemResponse:
    def test_from_attributes_enabled(self):
        assert CoordinationItemResponse.model_config.get("from_attributes") is True

    def test_stores_status(self):
        r = CoordinationItemResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            title="T", status="OPEN"
        )
        assert r.status == "OPEN"

    def test_optional_fields_none_by_default(self):
        r = CoordinationItemResponse(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            title="T", status="OPEN"
        )
        assert r.description is None
        assert r.assignee_id is None
        assert r.due_date is None
        assert r.source_event_id is None
        assert r.stage_timestamps is None
        assert r.created_at is None


class TestStatusTransitionRequest:
    def test_stores_to_status(self):
        r = StatusTransitionRequest(to_status="ACKNOWLEDGED")
        assert r.to_status == "ACKNOWLEDGED"


class TestCoordinationClosureResponse:
    def test_from_attributes_enabled(self):
        assert CoordinationClosureResponse.model_config.get("from_attributes") is True

    def test_stores_coordination_item_id(self):
        cid = uuid.uuid4()
        r = CoordinationClosureResponse(id=uuid.uuid4(), coordination_item_id=cid)
        assert r.coordination_item_id == cid

    def test_optional_fields(self):
        r = CoordinationClosureResponse(id=uuid.uuid4(), coordination_item_id=uuid.uuid4())
        assert r.closed_by is None
        assert r.closed_at is None
        assert r.resolution_notes is None


class TestCoordinationSummaryResponse:
    def test_stores_total(self):
        r = CoordinationSummaryResponse(total=5, open_count=3, overdue_count=1, by_status={})
        assert r.total == 5

    def test_stores_open_count(self):
        r = CoordinationSummaryResponse(total=5, open_count=3, overdue_count=1, by_status={})
        assert r.open_count == 3

    def test_stores_overdue_count(self):
        r = CoordinationSummaryResponse(total=5, open_count=3, overdue_count=1, by_status={})
        assert r.overdue_count == 1

    def test_stores_by_status(self):
        by = {"OPEN": 3, "CLOSED": 2}
        r = CoordinationSummaryResponse(total=5, open_count=3, overdue_count=0, by_status=by)
        assert r.by_status == by

    def test_zero_counts_valid(self):
        r = CoordinationSummaryResponse(total=0, open_count=0, overdue_count=0, by_status={})
        assert r.total == 0
