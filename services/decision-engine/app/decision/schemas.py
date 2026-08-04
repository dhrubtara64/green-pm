"""Decision Engine value objects and API schemas — S15-01, S15-02, S15-03, S15-04."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_DECISION_STATES: frozenset[str] = frozenset({
    "DRAFT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "AWAITING_INPUT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "DEFERRED",
    "SUPERSEDED",
    "ARCHIVED",
})
_PRIORITY_LEVELS: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
_IMPACT_LEVELS: frozenset[str] = frozenset({"LOW", "MEDIUM", "HIGH"})


@dataclass(frozen=True)
class DecisionQuery:
    project_id: uuid.UUID
    lifecycle_status: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lifecycle_status is not None and self.lifecycle_status not in _DECISION_STATES:
            raise ValueError(
                f"lifecycle_status must be one of {_DECISION_STATES}, got {self.lifecycle_status!r}"
            )


class DecisionCreate(BaseModel):
    project_id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: str = "MEDIUM"
    impact_level: str = "LOW"
    approval_required: bool = False

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be empty")
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str) -> str:
        if v not in _PRIORITY_LEVELS:
            raise ValueError(f"priority must be one of {_PRIORITY_LEVELS}")
        return v

    @field_validator("impact_level")
    @classmethod
    def impact_level_valid(cls, v: str) -> str:
        if v not in _IMPACT_LEVELS:
            raise ValueError(f"impact_level must be one of {_IMPACT_LEVELS}")
        return v


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: Optional[str] = None
    lifecycle_status: str
    priority: str
    impact_level: str
    approval_required: bool
    approval_count: int
    historical_context: list = []
    created_at: Optional[datetime] = None


class DecisionOptionCreate(BaseModel):
    decision_id: uuid.UUID
    option_text: str
    pros: Optional[str] = None
    cons: Optional[str] = None

    @field_validator("option_text")
    @classmethod
    def option_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("option_text must not be empty")
        return v


class DecisionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    decision_id: uuid.UUID
    option_text: str
    pros: Optional[str] = None
    cons: Optional[str] = None
    is_selected: bool = False


class DecisionApprovalCreate(BaseModel):
    decision_id: uuid.UUID
    approver_id: uuid.UUID
    approved: bool
    comment: Optional[str] = None


class DecisionApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    decision_id: uuid.UUID
    approver_id: uuid.UUID
    approved: bool
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
