"""Organizational Alignment Engine schemas — S14-04, S14-05, S14-06."""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_GAP_TYPES: frozenset[str] = frozenset({"UNCONFIRMED_RECEIPT", "UNACKNOWLEDGED"})
_SEVERITY_LEVELS: frozenset[str] = frozenset({"HIGH", "MEDIUM", "LOW"})

UNCONFIRMED_THRESHOLD_HOURS: int = 24
UNACKNOWLEDGED_SLA_HOURS: int = 48


@dataclass(frozen=True)
class AlignmentGapResult:
    receipt_id: uuid.UUID
    stakeholder_id: uuid.UUID
    event_type: str
    gap_type: str
    severity: str
    hours_overdue: float


class AlignmentReceiptCreate(BaseModel):
    project_id: uuid.UUID
    stakeholder_id: uuid.UUID
    event_id: str
    event_type: str

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event_type must be non-empty")
        return v

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event_id must be non-empty")
        return v


class AlignmentReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    stakeholder_id: uuid.UUID
    event_id: str
    event_type: str
    sent_at: Optional[datetime] = None
    receipt_confirmed_at: Optional[datetime] = None
    acknowledgment_confirmed_at: Optional[datetime] = None


class AlignmentGapResponse(BaseModel):
    receipt_id: uuid.UUID
    stakeholder_id: uuid.UUID
    event_type: str
    gap_type: str
    severity: str
    hours_overdue: float


class StakeholderAlignmentStatus(BaseModel):
    stakeholder_id: uuid.UUID
    total_events: int
    confirmed_receipts: int
    acknowledged: int
    pending_receipts: int
    pending_acknowledgments: int


class AlignmentMapResponse(BaseModel):
    project_id: uuid.UUID
    stakeholders: list[StakeholderAlignmentStatus]
    total_receipts: int
    unconfirmed_count: int
    unacknowledged_count: int
