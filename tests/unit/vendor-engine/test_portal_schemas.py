"""Tests for vendor portal API schemas — S8-04."""
import uuid
from datetime import datetime, timezone

import pytest

from app.portal.schemas import (
    VendorPortalRFIResponse,
    VendorPortalScoreResponse,
    VendorPortalSummaryResponse,
)


class TestVendorPortalScoreResponse:
    def test_stores_vendor_id(self):
        vid = uuid.uuid4()
        resp = VendorPortalScoreResponse(
            vendor_id=vid,
            overall_score=75.0,
            dimension_scores={"quality": 80.0},
            trend_direction="STABLE",
            predicted_score_30d=75.0,
        )
        assert resp.vendor_id == vid

    def test_stores_overall_score(self):
        resp = VendorPortalScoreResponse(
            vendor_id=uuid.uuid4(),
            overall_score=82.5,
            dimension_scores={},
            trend_direction="IMPROVING",
            predicted_score_30d=85.0,
        )
        assert resp.overall_score == 82.5

    def test_stores_trend_direction(self):
        resp = VendorPortalScoreResponse(
            vendor_id=uuid.uuid4(),
            overall_score=70.0,
            dimension_scores={},
            trend_direction="DECLINING",
            predicted_score_30d=65.0,
        )
        assert resp.trend_direction == "DECLINING"

    def test_stores_predicted_score(self):
        resp = VendorPortalScoreResponse(
            vendor_id=uuid.uuid4(),
            overall_score=70.0,
            dimension_scores={},
            trend_direction="STABLE",
            predicted_score_30d=71.5,
        )
        assert resp.predicted_score_30d == 71.5

    def test_computed_at_optional(self):
        resp = VendorPortalScoreResponse(
            vendor_id=uuid.uuid4(),
            overall_score=70.0,
            dimension_scores={},
            trend_direction="STABLE",
            predicted_score_30d=70.0,
        )
        assert resp.computed_at is None

    def test_from_attributes_enabled(self):
        assert VendorPortalScoreResponse.model_config.get("from_attributes") is True

    def test_dimension_scores_is_dict(self):
        resp = VendorPortalScoreResponse(
            vendor_id=uuid.uuid4(),
            overall_score=70.0,
            dimension_scores={"quality": 80.0, "delivery": 75.0},
            trend_direction="STABLE",
            predicted_score_30d=70.0,
        )
        assert isinstance(resp.dimension_scores, dict)
        assert resp.dimension_scores["quality"] == 80.0


class TestVendorPortalRFIResponse:
    def test_stores_rfi_number(self):
        resp = VendorPortalRFIResponse(
            id=uuid.uuid4(),
            rfi_number="RFI-042",
            title="Steel specification",
            status="OPEN",
        )
        assert resp.rfi_number == "RFI-042"

    def test_stores_title(self):
        resp = VendorPortalRFIResponse(
            id=uuid.uuid4(),
            rfi_number="RFI-001",
            title="Delivery schedule clarification",
            status="RESPONDED",
        )
        assert resp.title == "Delivery schedule clarification"

    def test_stores_status(self):
        resp = VendorPortalRFIResponse(
            id=uuid.uuid4(),
            rfi_number="RFI-001",
            title="X",
            status="CLOSED",
        )
        assert resp.status == "CLOSED"

    def test_responded_at_optional(self):
        resp = VendorPortalRFIResponse(
            id=uuid.uuid4(),
            rfi_number="RFI-001",
            title="X",
            status="OPEN",
        )
        assert resp.responded_at is None

    def test_from_attributes_enabled(self):
        assert VendorPortalRFIResponse.model_config.get("from_attributes") is True


class TestVendorPortalSummaryResponse:
    def test_stores_vendor_id(self):
        vid = uuid.uuid4()
        resp = VendorPortalSummaryResponse(
            vendor_id=vid,
            overall_score=72.0,
            trend_direction="STABLE",
            open_rfi_count=3,
        )
        assert resp.vendor_id == vid

    def test_stores_overall_score(self):
        resp = VendorPortalSummaryResponse(
            vendor_id=uuid.uuid4(),
            overall_score=88.5,
            trend_direction="IMPROVING",
            open_rfi_count=0,
        )
        assert resp.overall_score == 88.5

    def test_stores_open_rfi_count(self):
        resp = VendorPortalSummaryResponse(
            vendor_id=uuid.uuid4(),
            overall_score=70.0,
            trend_direction="STABLE",
            open_rfi_count=7,
        )
        assert resp.open_rfi_count == 7

    def test_last_scored_at_optional(self):
        resp = VendorPortalSummaryResponse(
            vendor_id=uuid.uuid4(),
            overall_score=70.0,
            trend_direction="STABLE",
            open_rfi_count=0,
        )
        assert resp.last_scored_at is None
