"""Scheduling logic for weekly report generation — S17-05.

Pure functions only: no IO, no async, no DB access.
Cloud Scheduler triggers the actual HTTP endpoint at Sunday 23:00;
these functions encode the business rules around scheduling, retry, and event emission.
"""
from __future__ import annotations

from typing import Optional

from app.reporting.schemas import ReportCreate

WEEKLY_SCHEDULE_DAY: str = "SUNDAY"
WEEKLY_SCHEDULE_TIME: str = "23:00"
SCHEDULED_REPORT_TYPE: str = "WEEKLY_SUMMARY"
_MAX_RETRIES: int = 1

# Event emitted on successful completion — consumed by downstream services
REPORT_GENERATED_EVENT: str = "report.generated"


def build_weekly_report_spec(
    project_id,
    title: Optional[str] = None,
) -> ReportCreate:
    """Build a ReportCreate for the Sunday 23:00 weekly scheduled generation."""
    return ReportCreate(
        project_id=project_id,
        report_type=SCHEDULED_REPORT_TYPE,
        title=title or "Weekly Project Summary",
        scheduled=True,
    )


def should_retry(attempt: int, max_retries: int = _MAX_RETRIES) -> bool:
    """Return True if the generation attempt warrants a retry.

    Reports get exactly one retry on failure before being marked FAILED.
    """
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    return attempt < max_retries


def build_generated_event_payload(
    report_id,
    project_id,
    report_type: str,
) -> dict:
    """Build the event payload emitted after successful report generation."""
    return {
        "event_type": REPORT_GENERATED_EVENT,
        "report_id": str(report_id),
        "project_id": str(project_id),
        "report_type": report_type,
    }


def is_scheduled_report_type(report_type: str) -> bool:
    """Return True if the report type is eligible for Cloud Scheduler generation."""
    return report_type == SCHEDULED_REPORT_TYPE


def generation_log_line(report_id, report_type: str, attempt: int, success: bool) -> str:
    """Build a structured log line for a report generation attempt."""
    status = "SUCCESS" if success else "FAILURE"
    return f"[report.generation] id={report_id} type={report_type} attempt={attempt} status={status}"
