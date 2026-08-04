"""Tests for Organizational Alignment Engine schemas — S14-04, S14-05, S14-06."""
import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.alignment.schemas import (
    UNACKNOWLEDGED_SLA_HOURS,
    UNCONFIRMED_THRESHOLD_HOURS,
    AlignmentGapResponse,
    AlignmentGapResult,
    AlignmentMapResponse,
    AlignmentReceiptCreate,
    AlignmentReceiptResponse,
    StakeholderAlignmentStatus,
    _GAP_TYPES,
    _SEVERITY_LEVELS,
)


class TestGapTypesConstant:
    def test_is_frozenset(self):
        assert isinstance(_GAP_TYPES, frozenset)

    def test_has_two_types(self):
        assert len(_GAP_TYPES) == 2

    def test_unconfirmed_receipt_present(self):
        assert "UNCONFIRMED_RECEIPT" in _GAP_TYPES

    def test_unacknowledged_present(self):
        assert "UNACKNOWLEDGED" in _GAP_TYPES


class TestSeverityLevelsConstant:
    def test_is_frozenset(self):
        assert isinstance(_SEVERITY_LEVELS, frozenset)

    def test_has_three_levels(self):
        assert len(_SEVERITY_LEVELS) == 3

    def test_high_present(self):
        assert "HIGH" in _SEVERITY_LEVELS

    def test_medium_present(self):
        assert "MEDIUM" in _SEVERITY_LEVELS

    def test_low_present(self):
        assert "LOW" in _SEVERITY_LEVELS


class TestThresholdConstants:
    def test_unconfirmed_threshold_is_24(self):
        assert UNCONFIRMED_THRESHOLD_HOURS == 24

    def test_unacknowledged_sla_is_48(self):
        assert UNACKNOWLEDGED_SLA_HOURS == 48


class TestAlignmentGapResult:
    def _make(self, **kw) -> AlignmentGapResult:
        base = dict(
            receipt_id=uuid.uuid4(),
            stakeholder_id=uuid.uuid4(),
            event_type="RiskIdentified",
            gap_type="UNCONFIRMED_RECEIPT",
            severity="HIGH",
            hours_overdue=30.0,
        )
        return AlignmentGapResult(**{**base, **kw})

    def test_stores_receipt_id(self):
        rid = uuid.uuid4()
        assert self._make(receipt_id=rid).receipt_id == rid

    def test_stores_stakeholder_id(self):
        sid = uuid.uuid4()
        assert self._make(stakeholder_id=sid).stakeholder_id == sid

    def test_stores_event_type(self):
        assert self._make().event_type == "RiskIdentified"

    def test_stores_gap_type(self):
        assert self._make(gap_type="UNACKNOWLEDGED").gap_type == "UNACKNOWLEDGED"

    def test_stores_severity(self):
        assert self._make(severity="MEDIUM").severity == "MEDIUM"

    def test_stores_hours_overdue(self):
        assert self._make(hours_overdue=12.5).hours_overdue == pytest.approx(12.5)

    def test_is_frozen(self):
        g = self._make()
        with pytest.raises(FrozenInstanceError):
            g.severity = "LOW"  # type: ignore[misc]


class TestAlignmentReceiptCreate:
    def _pid(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_stores_project_id(self):
        pid = self._pid()
        c = AlignmentReceiptCreate(
            project_id=pid, stakeholder_id=uuid.uuid4(), event_id="evt-1", event_type="RiskIdentified"
        )
        assert c.project_id == pid

    def test_stores_stakeholder_id(self):
        sid = uuid.uuid4()
        c = AlignmentReceiptCreate(
            project_id=self._pid(), stakeholder_id=sid, event_id="evt-1", event_type="RiskIdentified"
        )
        assert c.stakeholder_id == sid

    def test_stores_event_id(self):
        c = AlignmentReceiptCreate(
            project_id=self._pid(), stakeholder_id=uuid.uuid4(),
            event_id="evt-abc-123", event_type="VendorDelayFlagged"
        )
        assert c.event_id == "evt-abc-123"

    def test_stores_event_type(self):
        c = AlignmentReceiptCreate(
            project_id=self._pid(), stakeholder_id=uuid.uuid4(),
            event_id="e1", event_type="CriticalPathChanged"
        )
        assert c.event_type == "CriticalPathChanged"

    def test_empty_event_type_raises(self):
        with pytest.raises(ValidationError):
            AlignmentReceiptCreate(
                project_id=self._pid(), stakeholder_id=uuid.uuid4(),
                event_id="e1", event_type=""
            )

    def test_empty_event_id_raises(self):
        with pytest.raises(ValidationError):
            AlignmentReceiptCreate(
                project_id=self._pid(), stakeholder_id=uuid.uuid4(),
                event_id="", event_type="SomeEvent"
            )


class TestAlignmentReceiptResponse:
    def test_from_attributes_enabled(self):
        assert AlignmentReceiptResponse.model_config.get("from_attributes") is True

    def test_stores_required_fields(self):
        r = AlignmentReceiptResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            stakeholder_id=uuid.uuid4(),
            event_id="e1",
            event_type="RiskIdentified",
        )
        assert r.event_type == "RiskIdentified"

    def test_optional_timestamps_default_none(self):
        r = AlignmentReceiptResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            stakeholder_id=uuid.uuid4(),
            event_id="e1",
            event_type="X",
        )
        assert r.sent_at is None
        assert r.receipt_confirmed_at is None
        assert r.acknowledgment_confirmed_at is None


class TestAlignmentGapResponse:
    def test_stores_all_fields(self):
        r = AlignmentGapResponse(
            receipt_id=uuid.uuid4(),
            stakeholder_id=uuid.uuid4(),
            event_type="RiskIdentified",
            gap_type="UNCONFIRMED_RECEIPT",
            severity="HIGH",
            hours_overdue=30.0,
        )
        assert r.gap_type == "UNCONFIRMED_RECEIPT"
        assert r.severity == "HIGH"


class TestStakeholderAlignmentStatus:
    def test_stores_all_fields(self):
        s = StakeholderAlignmentStatus(
            stakeholder_id=uuid.uuid4(),
            total_events=10,
            confirmed_receipts=8,
            acknowledged=6,
            pending_receipts=2,
            pending_acknowledgments=2,
        )
        assert s.total_events == 10
        assert s.pending_receipts == 2


class TestAlignmentMapResponse:
    def test_stores_project_id(self):
        pid = uuid.uuid4()
        r = AlignmentMapResponse(
            project_id=pid, stakeholders=[], total_receipts=0,
            unconfirmed_count=0, unacknowledged_count=0
        )
        assert r.project_id == pid

    def test_zero_counts_valid(self):
        r = AlignmentMapResponse(
            project_id=uuid.uuid4(), stakeholders=[], total_receipts=0,
            unconfirmed_count=0, unacknowledged_count=0
        )
        assert r.total_receipts == 0
