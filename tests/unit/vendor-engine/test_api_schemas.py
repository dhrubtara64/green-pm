"""Tests for vendor API request/response schemas — S8-05."""
import uuid

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    RFICreate,
    RFIResponse,
    RFIStatusFilter,
    VendorCreate,
    VendorResponse,
    VendorScoreHistoryResponse,
    VendorScoreRequest,
    VendorScoreResponse,
)


class TestVendorCreate:
    def test_stores_name(self):
        v = VendorCreate(name="ACME Steel", project_id=uuid.uuid4())
        assert v.name == "ACME Steel"

    def test_stores_project_id(self):
        pid = uuid.uuid4()
        v = VendorCreate(name="Vendor A", project_id=pid)
        assert v.project_id == pid

    def test_vendor_code_optional(self):
        v = VendorCreate(name="Vendor A", project_id=uuid.uuid4())
        assert v.vendor_code is None

    def test_contact_email_optional(self):
        v = VendorCreate(name="Vendor A", project_id=uuid.uuid4())
        assert v.contact_email is None

    def test_vendor_code_stored(self):
        v = VendorCreate(name="Vendor A", project_id=uuid.uuid4(), vendor_code="V-001")
        assert v.vendor_code == "V-001"


class TestVendorResponse:
    def test_from_attributes_enabled(self):
        assert VendorResponse.model_config.get("from_attributes") is True

    def test_default_status_active(self):
        resp = VendorResponse(
            id=uuid.uuid4(),
            name="Vendor A",
            project_id=uuid.uuid4(),
        )
        assert resp.status == "active"


class TestVendorScoreRequest:
    def _valid(self, **overrides) -> dict:
        base = dict(
            quality=80.0, delivery=75.0, responsiveness=70.0,
            documentation=65.0, commercial=60.0, relationship=55.0,
        )
        return {**base, **overrides}

    def test_valid_request_parses(self):
        req = VendorScoreRequest(**self._valid())
        assert req.quality == 80.0

    def test_all_six_dimensions_stored(self):
        req = VendorScoreRequest(**self._valid())
        assert req.delivery == 75.0
        assert req.responsiveness == 70.0
        assert req.documentation == 65.0
        assert req.commercial == 60.0
        assert req.relationship == 55.0

    def test_weights_optional(self):
        req = VendorScoreRequest(**self._valid())
        assert req.weights is None

    def test_custom_weights_stored(self):
        req = VendorScoreRequest(**self._valid(), weights={"quality": 0.5, "delivery": 0.5})
        assert req.weights["quality"] == 0.5

    def test_quality_negative_raises(self):
        with pytest.raises(ValidationError):
            VendorScoreRequest(**self._valid(quality=-0.1))

    def test_delivery_over_100_raises(self):
        with pytest.raises(ValidationError):
            VendorScoreRequest(**self._valid(delivery=100.1))

    def test_zero_dimensions_valid(self):
        req = VendorScoreRequest(**self._valid(
            quality=0.0, delivery=0.0, responsiveness=0.0,
            documentation=0.0, commercial=0.0, relationship=0.0,
        ))
        assert req.quality == 0.0

    def test_hundred_dimensions_valid(self):
        req = VendorScoreRequest(**self._valid(
            quality=100.0, delivery=100.0, responsiveness=100.0,
            documentation=100.0, commercial=100.0, relationship=100.0,
        ))
        assert req.quality == 100.0


class TestVendorScoreResponse:
    def test_from_attributes_enabled(self):
        assert VendorScoreResponse.model_config.get("from_attributes") is True

    def test_stores_overall_score(self):
        resp = VendorScoreResponse(
            id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            overall_score=78.5,
            dimension_scores={"quality": 80.0},
            weights={"quality": 1.0},
        )
        assert resp.overall_score == 78.5


class TestRFIStatusFilter:
    def test_open_value(self):
        assert RFIStatusFilter.OPEN == "OPEN"

    def test_responded_value(self):
        assert RFIStatusFilter.RESPONDED == "RESPONDED"

    def test_closed_value(self):
        assert RFIStatusFilter.CLOSED == "CLOSED"

    def test_all_value(self):
        assert RFIStatusFilter.ALL == "ALL"

    def test_four_statuses_total(self):
        assert len(RFIStatusFilter) == 4


class TestRFICreate:
    def test_stores_rfi_number(self):
        rfi = RFICreate(rfi_number="RFI-001", title="Spec clarification")
        assert rfi.rfi_number == "RFI-001"

    def test_stores_title(self):
        rfi = RFICreate(rfi_number="RFI-001", title="Steel grade query")
        assert rfi.title == "Steel grade query"

    def test_description_optional(self):
        rfi = RFICreate(rfi_number="RFI-001", title="Query")
        assert rfi.description is None


class TestRFIResponse:
    def test_from_attributes_enabled(self):
        assert RFIResponse.model_config.get("from_attributes") is True

    def test_stores_rfi_number(self):
        resp = RFIResponse(
            id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            rfi_number="RFI-042",
            title="Clarify tolerances",
            status="OPEN",
        )
        assert resp.rfi_number == "RFI-042"

    def test_responded_at_optional(self):
        resp = RFIResponse(
            id=uuid.uuid4(),
            vendor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            rfi_number="RFI-001",
            title="X",
            status="OPEN",
        )
        assert resp.responded_at is None
