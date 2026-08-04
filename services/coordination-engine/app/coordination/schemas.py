"""Domain and API schemas for the Coordination Engine — S12-01, S12-03, S12-04."""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

_COORDINATION_STATUSES: frozenset[str] = frozenset(
    {"OPEN", "ACKNOWLEDGED", "EXECUTING", "VERIFIED", "CLOSED"}
)
_TERMINAL_STATUSES: frozenset[str] = frozenset({"VERIFIED", "CLOSED"})

_VALID_TRANSITIONS: dict[str, str] = {
    "OPEN": "ACKNOWLEDGED",
    "ACKNOWLEDGED": "EXECUTING",
    "EXECUTING": "VERIFIED",
    "VERIFIED": "CLOSED",
}


@dataclass(frozen=True)
class CoordinationTransition:
    item_id: uuid.UUID
    from_status: str
    to_status: str

    def __post_init__(self) -> None:
        if self.from_status not in _COORDINATION_STATUSES:
            raise ValueError(f"from_status {self.from_status!r} is not a valid coordination status")
        if self.to_status not in _COORDINATION_STATUSES:
            raise ValueError(f"to_status {self.to_status!r} is not a valid coordination status")
        allowed = _VALID_TRANSITIONS.get(self.from_status)
        if allowed != self.to_status:
            raise ValueError(
                f"Invalid transition: {self.from_status!r} → {self.to_status!r}. "
                f"Expected: {self.from_status!r} → {allowed!r}"
            )


class CoordinationItemCreate(BaseModel):
    project_id: uuid.UUID
    title: str
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    source_event_id: Optional[str] = None


class CoordinationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[date] = None
    source_event_id: Optional[str] = None
    stage_timestamps: Optional[dict] = None
    created_at: Optional[datetime] = None


class StatusTransitionRequest(BaseModel):
    to_status: str


class CoordinationClosureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    coordination_item_id: uuid.UUID
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class CoordinationSummaryResponse(BaseModel):
    total: int
    open_count: int
    overdue_count: int
    by_status: dict
