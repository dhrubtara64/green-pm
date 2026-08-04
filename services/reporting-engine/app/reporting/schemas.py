"""Domain schemas for the Reporting Engine — S17-01, S17-04, S17-05."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_REPORT_TYPES: frozenset[str] = frozenset({
    "WEEKLY_SUMMARY",
    "RISK_DIGEST",
    "VENDOR_SCORECARD",
    "READINESS_ASSESSMENT",
    "DECISION_REVIEW",
    "FORECAST_OUTLOOK",
    "ALIGNMENT_BRIEF",
    "EXECUTIVE_OVERVIEW",
})

_REPORT_STATUSES: frozenset[str] = frozenset({
    "PENDING",
    "GENERATING",
    "COMPLETE",
    "FAILED",
})


@dataclass(frozen=True)
class ReportSpec:
    """Pure value object describing a report to be generated — immutable."""

    project_id: uuid.UUID
    report_type: str
    title: str

    def __post_init__(self) -> None:
        if self.report_type not in _REPORT_TYPES:
            raise ValueError(f"Invalid report_type: {self.report_type!r}")
        if not self.title.strip():
            raise ValueError("title cannot be empty")


class ReportCreate(BaseModel):
    project_id: uuid.UUID
    report_type: str
    title: str
    structured_data: dict = {}
    scheduled: bool = False

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        if v not in _REPORT_TYPES:
            raise ValueError(f"Invalid report_type: {v!r}")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    report_type: str
    title: str
    narrative: Optional[str] = None
    structured_data: dict = {}
    evidence_chain_id: Optional[uuid.UUID] = None
    status: str
    generated_at: Optional[datetime] = None
    scheduled: bool = False


class ReportGenerateRequest(BaseModel):
    """Triggers async AI narrative generation for an existing report record."""

    report_id: uuid.UUID
    context_hint: Optional[str] = None
