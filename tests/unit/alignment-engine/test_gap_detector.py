"""Tests for pure gap-detection functions — S14-05."""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.alignment.gap_detector import detect_gaps, score_gap_severity
from app.alignment.schemas import AlignmentGapResult


def _receipt(
    sent_hours_ago: float,
    receipt_hours_ago: float | None = None,
    ack_hours_ago: float | None = None,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    r = MagicMock()
    r.id = uuid.uuid4()
    r.stakeholder_id = uuid.uuid4()
    r.event_type = "RiskIdentified"
    from datetime import timedelta
    r.sent_at = now - timedelta(hours=sent_hours_ago)
    r.receipt_confirmed_at = (
        now - timedelta(hours=receipt_hours_ago) if receipt_hours_ago is not None else None
    )
    r.acknowledgment_confirmed_at = (
        now - timedelta(hours=ack_hours_ago) if ack_hours_ago is not None else None
    )
    return r


class TestScoreGapSeverity:
    def test_overdue_above_48_is_high(self):
        assert score_gap_severity("UNCONFIRMED_RECEIPT", 49.0) == "HIGH"

    def test_overdue_exactly_48_is_medium(self):
        assert score_gap_severity("UNCONFIRMED_RECEIPT", 48.0) == "MEDIUM"

    def test_overdue_between_24_and_48_is_medium(self):
        assert score_gap_severity("UNACKNOWLEDGED", 36.0) == "MEDIUM"

    def test_overdue_exactly_24_is_low(self):
        assert score_gap_severity("UNACKNOWLEDGED", 24.0) == "LOW"

    def test_overdue_below_24_is_low(self):
        assert score_gap_severity("UNCONFIRMED_RECEIPT", 10.0) == "LOW"

    def test_zero_overdue_is_low(self):
        assert score_gap_severity("UNACKNOWLEDGED", 0.0) == "LOW"

    def test_works_for_unconfirmed_receipt_type(self):
        assert score_gap_severity("UNCONFIRMED_RECEIPT", 100.0) == "HIGH"

    def test_works_for_unacknowledged_type(self):
        assert score_gap_severity("UNACKNOWLEDGED", 100.0) == "HIGH"


class TestDetectGaps:
    def _now(self):
        return datetime.now(timezone.utc)

    def test_empty_receipts_returns_empty(self):
        assert detect_gaps([], self._now()) == []

    def test_receipt_within_threshold_not_flagged(self):
        r = _receipt(sent_hours_ago=10)  # 10h < 24h threshold
        assert detect_gaps([r], self._now()) == []

    def test_unconfirmed_receipt_flagged_after_threshold(self):
        r = _receipt(sent_hours_ago=30)  # 30h > 24h threshold, no confirmation
        gaps = detect_gaps([r], self._now())
        assert len(gaps) == 1
        assert gaps[0].gap_type == "UNCONFIRMED_RECEIPT"

    def test_confirmed_receipt_within_sla_not_flagged(self):
        r = _receipt(sent_hours_ago=30, receipt_hours_ago=20)  # confirmed 20h ago, 20h < 48h SLA
        assert detect_gaps([r], self._now()) == []

    def test_unacknowledged_flagged_after_sla(self):
        r = _receipt(sent_hours_ago=60, receipt_hours_ago=50)  # confirmed 50h ago > 48h SLA
        gaps = detect_gaps([r], self._now())
        assert len(gaps) == 1
        assert gaps[0].gap_type == "UNACKNOWLEDGED"

    def test_acknowledged_receipt_not_flagged(self):
        r = _receipt(sent_hours_ago=72, receipt_hours_ago=60, ack_hours_ago=10)
        assert detect_gaps([r], self._now()) == []

    def test_returns_alignment_gap_result_objects(self):
        r = _receipt(sent_hours_ago=30)
        gaps = detect_gaps([r], self._now())
        assert all(isinstance(g, AlignmentGapResult) for g in gaps)

    def test_gap_result_has_correct_receipt_id(self):
        r = _receipt(sent_hours_ago=30)
        gaps = detect_gaps([r], self._now())
        assert gaps[0].receipt_id == r.id

    def test_gap_result_has_correct_stakeholder_id(self):
        r = _receipt(sent_hours_ago=30)
        gaps = detect_gaps([r], self._now())
        assert gaps[0].stakeholder_id == r.stakeholder_id

    def test_gap_result_has_correct_event_type(self):
        r = _receipt(sent_hours_ago=30)
        gaps = detect_gaps([r], self._now())
        assert gaps[0].event_type == "RiskIdentified"

    def test_gap_hours_overdue_positive(self):
        r = _receipt(sent_hours_ago=30)  # 30 - 24 = 6h overdue
        gaps = detect_gaps([r], self._now())
        assert gaps[0].hours_overdue > 0

    def test_sorted_high_before_low(self):
        r_high = _receipt(sent_hours_ago=100)  # very overdue → HIGH
        r_low = _receipt(sent_hours_ago=26)    # slightly overdue → LOW
        gaps = detect_gaps([r_low, r_high], self._now())
        assert gaps[0].severity == "HIGH"
        assert gaps[-1].severity == "LOW"

    def test_mixed_gap_types_both_detected(self):
        r_unconfirmed = _receipt(sent_hours_ago=30)
        r_unacked = _receipt(sent_hours_ago=60, receipt_hours_ago=50)
        gaps = detect_gaps([r_unconfirmed, r_unacked], self._now())
        gap_types = {g.gap_type for g in gaps}
        assert "UNCONFIRMED_RECEIPT" in gap_types
        assert "UNACKNOWLEDGED" in gap_types

    def test_no_sent_at_skipped(self):
        r = MagicMock()
        r.sent_at = None
        r.receipt_confirmed_at = None
        r.acknowledgment_confirmed_at = None
        r.id = uuid.uuid4()
        r.stakeholder_id = uuid.uuid4()
        r.event_type = "X"
        assert detect_gaps([r], self._now()) == []

    def test_custom_threshold_respected(self):
        r = _receipt(sent_hours_ago=10)  # 10h > 8h custom threshold
        gaps = detect_gaps([r], self._now(), unconfirmed_threshold_hours=8)
        assert len(gaps) == 1

    def test_custom_sla_respected(self):
        r = _receipt(sent_hours_ago=40, receipt_hours_ago=30)  # confirmed 30h ago > 20h custom SLA
        gaps = detect_gaps([r], self._now(), unacknowledged_sla_hours=20)
        assert len(gaps) == 1
        assert gaps[0].gap_type == "UNACKNOWLEDGED"
