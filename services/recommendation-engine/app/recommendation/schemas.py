"""Domain schemas for the Recommendation Engine — S16-01."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_SIGNAL_TYPES: frozenset[str] = frozenset({
    "RISK",
    "DELAY",
    "VENDOR_ISSUE",
    "READINESS_GAP",
    "DEPENDENCY_CONFLICT",
    "ALIGNMENT_GAP",
    "FORECAST_DEVIATION",
    "DECISION_PENDING",
    "INCONSISTENCY",
    "MEMORY_PATTERN",
    "SUPPLY_SHORTAGE",
    "COORDINATION_FAILURE",
    "SIMULATION_ALERT",
    "EVIDENCE_MISSING",
    "IMPACT_ESCALATION",
    "GENERAL",
})

_STATUSES: frozenset[str] = frozenset({"ACTIVE", "ACTIONED", "DISMISSED"})

SUPPORTED_ENGINES: frozenset[str] = frozenset({
    "evidence-engine",
    "impact-engine",
    "dependency-engine",
    "supply-chain-engine",
    "vendor-engine",
    "risk-engine",
    "readiness-engine",
    "simulation-engine",
    "coordination-engine",
    "organizational-memory",
    "forecasting-engine",
    "alignment-engine",
    "decision-engine",
    "sync-engine",
    "pig-service",
    "core-platform",
})


@dataclass(frozen=True)
class RecommendationSignal:
    """Pure value object carrying a signal from one engine — immutable."""

    engine_name: str
    signal_type: str
    priority_score: float
    entity_id: uuid.UUID
    title: str
    description: str

    def __post_init__(self) -> None:
        if self.engine_name not in SUPPORTED_ENGINES:
            raise ValueError(f"Unknown engine: {self.engine_name!r}")
        if self.signal_type not in _SIGNAL_TYPES:
            raise ValueError(f"Invalid signal_type: {self.signal_type!r}")
        if not (0.0 <= self.priority_score <= 1.0):
            raise ValueError(
                f"priority_score must be in [0.0, 1.0], got {self.priority_score}"
            )
        if not self.title.strip():
            raise ValueError("title cannot be empty")


class RecommendationCreate(BaseModel):
    project_id: uuid.UUID
    engine_name: str
    signal_type: str
    priority_score: float
    title: str
    description: str
    projected_outcome: Optional[str] = None
    responsible_party: Optional[str] = None
    evidence_ids: list[uuid.UUID] = []

    @field_validator("engine_name")
    @classmethod
    def validate_engine_name(cls, v: str) -> str:
        if v not in SUPPORTED_ENGINES:
            raise ValueError(f"Unknown engine: {v!r}")
        return v

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        if v not in _SIGNAL_TYPES:
            raise ValueError(f"Invalid signal_type: {v!r}")
        return v

    @field_validator("priority_score")
    @classmethod
    def validate_priority_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("priority_score must be in [0.0, 1.0]")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description cannot be empty")
        return v


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    engine_name: str
    signal_type: str
    priority_score: float
    title: str
    description: str
    projected_outcome: Optional[str] = None
    responsible_party: Optional[str] = None
    evidence_ids: list = []
    status: str
    created_at: Optional[datetime] = None


class RecommendationStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _STATUSES:
            raise ValueError(f"Invalid status: {v!r}. Must be one of {_STATUSES}")
        return v
