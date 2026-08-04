"""Tests for Reporting Engine scheduling logic — S17-05."""
import uuid

import pytest

from app.reporting.schemas import ReportCreate
from app.reporting.scheduler import (
    REPORT_GENERATED_EVENT,
    SCHEDULED_REPORT_TYPE,
    WEEKLY_SCHEDULE_DAY,
    WEEKLY_SCHEDULE_TIME,
    _MAX_RETRIES,
    build_generated_event_payload,
    build_weekly_report_spec,
    generation_log_line,
    is_scheduled_report_type,
    should_retry,
)


class TestScheduleConstants:
    def test_weekly_schedule_day_is_sunday(self):
        assert WEEKLY_SCHEDULE_DAY == "SUNDAY"

    def test_weekly_schedule_time_is_23_00(self):
        assert WEEKLY_SCHEDULE_TIME == "23:00"

    def test_scheduled_report_type_is_weekly(self):
        assert SCHEDULED_REPORT_TYPE == "WEEKLY_SUMMARY"

    def test_report_generated_event_name(self):
        assert REPORT_GENERATED_EVENT == "report.generated"

    def test_max_retries_is_one(self):
        assert _MAX_RETRIES == 1


class TestBuildWeeklyReportSpec:
    def test_returns_report_create(self):
        spec = build_weekly_report_spec(uuid.uuid4())
        assert isinstance(spec, ReportCreate)

    def test_report_type_is_weekly_summary(self):
        spec = build_weekly_report_spec(uuid.uuid4())
        assert spec.report_type == SCHEDULED_REPORT_TYPE

    def test_scheduled_is_true(self):
        spec = build_weekly_report_spec(uuid.uuid4())
        assert spec.scheduled is True

    def test_project_id_stored(self):
        pid = uuid.uuid4()
        spec = build_weekly_report_spec(pid)
        assert spec.project_id == pid

    def test_default_title_non_empty(self):
        spec = build_weekly_report_spec(uuid.uuid4())
        assert len(spec.title) > 0

    def test_custom_title_used(self):
        spec = build_weekly_report_spec(uuid.uuid4(), title="Sprint 17 Report")
        assert spec.title == "Sprint 17 Report"


class TestShouldRetry:
    def test_attempt_zero_should_retry(self):
        assert should_retry(0) is True

    def test_attempt_one_should_not_retry_by_default(self):
        assert should_retry(1) is False

    def test_attempt_two_should_not_retry(self):
        assert should_retry(2) is False

    def test_custom_max_retries_zero(self):
        assert should_retry(0, max_retries=0) is False

    def test_custom_max_retries_two(self):
        assert should_retry(1, max_retries=2) is True
        assert should_retry(2, max_retries=2) is False

    def test_negative_attempt_raises(self):
        with pytest.raises(ValueError):
            should_retry(-1)

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError):
            should_retry(0, max_retries=-1)


class TestBuildGeneratedEventPayload:
    def test_returns_dict(self):
        result = build_generated_event_payload(uuid.uuid4(), uuid.uuid4(), "WEEKLY_SUMMARY")
        assert isinstance(result, dict)

    def test_event_type_correct(self):
        result = build_generated_event_payload(uuid.uuid4(), uuid.uuid4(), "WEEKLY_SUMMARY")
        assert result["event_type"] == REPORT_GENERATED_EVENT

    def test_report_id_in_payload(self):
        rid = uuid.uuid4()
        result = build_generated_event_payload(rid, uuid.uuid4(), "WEEKLY_SUMMARY")
        assert result["report_id"] == str(rid)

    def test_project_id_in_payload(self):
        pid = uuid.uuid4()
        result = build_generated_event_payload(uuid.uuid4(), pid, "WEEKLY_SUMMARY")
        assert result["project_id"] == str(pid)

    def test_report_type_in_payload(self):
        result = build_generated_event_payload(uuid.uuid4(), uuid.uuid4(), "RISK_DIGEST")
        assert result["report_type"] == "RISK_DIGEST"


class TestIsScheduledReportType:
    def test_weekly_summary_is_scheduled(self):
        assert is_scheduled_report_type("WEEKLY_SUMMARY") is True

    def test_other_types_not_scheduled(self):
        assert is_scheduled_report_type("RISK_DIGEST") is False
        assert is_scheduled_report_type("EXECUTIVE_OVERVIEW") is False

    def test_unknown_type_not_scheduled(self):
        assert is_scheduled_report_type("UNKNOWN") is False


class TestGenerationLogLine:
    def test_returns_string(self):
        result = generation_log_line(uuid.uuid4(), "WEEKLY_SUMMARY", 0, True)
        assert isinstance(result, str)

    def test_success_log_contains_success(self):
        result = generation_log_line(uuid.uuid4(), "WEEKLY_SUMMARY", 0, True)
        assert "SUCCESS" in result

    def test_failure_log_contains_failure(self):
        result = generation_log_line(uuid.uuid4(), "WEEKLY_SUMMARY", 0, False)
        assert "FAILURE" in result

    def test_log_contains_report_type(self):
        result = generation_log_line(uuid.uuid4(), "RISK_DIGEST", 0, True)
        assert "RISK_DIGEST" in result

    def test_log_contains_attempt(self):
        result = generation_log_line(uuid.uuid4(), "WEEKLY_SUMMARY", 1, False)
        assert "1" in result
