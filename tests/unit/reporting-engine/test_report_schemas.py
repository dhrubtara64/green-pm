"""Tests for Reporting Engine schemas — S17-01, S17-04."""
import uuid

import pytest
from pydantic import ValidationError

from app.reporting.schemas import (
    ReportCreate,
    ReportGenerateRequest,
    ReportResponse,
    ReportSpec,
    _REPORT_STATUSES,
    _REPORT_TYPES,
)


class TestReportTypes:
    def test_has_eight_types(self):
        assert len(_REPORT_TYPES) == 8

    def test_is_frozenset(self):
        assert isinstance(_REPORT_TYPES, frozenset)

    def test_weekly_summary_present(self):
        assert "WEEKLY_SUMMARY" in _REPORT_TYPES

    def test_executive_overview_present(self):
        assert "EXECUTIVE_OVERVIEW" in _REPORT_TYPES

    def test_risk_digest_present(self):
        assert "RISK_DIGEST" in _REPORT_TYPES

    def test_all_types_are_strings(self):
        assert all(isinstance(t, str) for t in _REPORT_TYPES)


class TestReportStatuses:
    def test_pending_present(self):
        assert "PENDING" in _REPORT_STATUSES

    def test_complete_present(self):
        assert "COMPLETE" in _REPORT_STATUSES

    def test_failed_present(self):
        assert "FAILED" in _REPORT_STATUSES

    def test_generating_present(self):
        assert "GENERATING" in _REPORT_STATUSES

    def test_is_frozenset(self):
        assert isinstance(_REPORT_STATUSES, frozenset)


class TestReportSpec:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            report_type="WEEKLY_SUMMARY",
            title="Q3 Weekly Report",
        )
        defaults.update(kwargs)
        return ReportSpec(**defaults)

    def test_creates_successfully(self):
        spec = self._make()
        assert spec.report_type == "WEEKLY_SUMMARY"

    def test_is_frozen(self):
        spec = self._make()
        with pytest.raises((AttributeError, TypeError)):
            spec.title = "changed"  # type: ignore[misc]

    def test_project_id_stored(self):
        pid = uuid.uuid4()
        spec = self._make(project_id=pid)
        assert spec.project_id == pid

    def test_title_stored(self):
        spec = self._make(title="My Report")
        assert spec.title == "My Report"

    def test_invalid_report_type_raises(self):
        with pytest.raises(ValueError, match="Invalid report_type"):
            self._make(report_type="UNKNOWN_TYPE")

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            self._make(title="  ")

    def test_all_report_types_valid(self):
        for rt in _REPORT_TYPES:
            spec = self._make(report_type=rt)
            assert spec.report_type == rt


class TestReportCreate:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            report_type="WEEKLY_SUMMARY",
            title="My Report",
        )
        defaults.update(kwargs)
        return ReportCreate(**defaults)

    def test_creates_successfully(self):
        rc = self._make()
        assert rc.title == "My Report"

    def test_structured_data_defaults_empty(self):
        rc = self._make()
        assert rc.structured_data == {}

    def test_scheduled_defaults_false(self):
        rc = self._make()
        assert rc.scheduled is False

    def test_scheduled_true_accepted(self):
        rc = self._make(scheduled=True)
        assert rc.scheduled is True

    def test_invalid_report_type_raises(self):
        with pytest.raises(ValidationError):
            self._make(report_type="GARBAGE_TYPE")

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            self._make(title="")

    def test_whitespace_title_raises(self):
        with pytest.raises(ValidationError):
            self._make(title="   ")

    def test_structured_data_accepted(self):
        rc = self._make(structured_data={"key": "value", "count": 5})
        assert rc.structured_data["count"] == 5

    def test_all_report_types_accepted(self):
        for rt in _REPORT_TYPES:
            rc = self._make(report_type=rt)
            assert rc.report_type == rt

    def test_project_id_stored(self):
        pid = uuid.uuid4()
        rc = self._make(project_id=pid)
        assert rc.project_id == pid


class TestReportResponse:
    def _make_dict(self, **kwargs):
        defaults = dict(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            report_type="WEEKLY_SUMMARY",
            title="My Report",
            status="PENDING",
        )
        defaults.update(kwargs)
        return defaults

    def test_creates_from_dict(self):
        resp = ReportResponse(**self._make_dict())
        assert resp.status == "PENDING"

    def test_narrative_defaults_none(self):
        resp = ReportResponse(**self._make_dict())
        assert resp.narrative is None

    def test_structured_data_defaults_empty(self):
        resp = ReportResponse(**self._make_dict())
        assert resp.structured_data == {}

    def test_evidence_chain_id_defaults_none(self):
        resp = ReportResponse(**self._make_dict())
        assert resp.evidence_chain_id is None

    def test_generated_at_defaults_none(self):
        resp = ReportResponse(**self._make_dict())
        assert resp.generated_at is None

    def test_scheduled_defaults_false(self):
        resp = ReportResponse(**self._make_dict())
        assert resp.scheduled is False

    def test_from_attributes_config(self):
        assert ReportResponse.model_config.get("from_attributes") is True

    def test_evidence_chain_id_accepted(self):
        cid = uuid.uuid4()
        resp = ReportResponse(**self._make_dict(evidence_chain_id=cid))
        assert resp.evidence_chain_id == cid


class TestReportGenerateRequest:
    def test_creates_successfully(self):
        req = ReportGenerateRequest(report_id=uuid.uuid4())
        assert isinstance(req.report_id, uuid.UUID)

    def test_context_hint_defaults_none(self):
        req = ReportGenerateRequest(report_id=uuid.uuid4())
        assert req.context_hint is None

    def test_context_hint_accepted(self):
        req = ReportGenerateRequest(
            report_id=uuid.uuid4(),
            context_hint="Focus on risk items.",
        )
        assert req.context_hint is not None
