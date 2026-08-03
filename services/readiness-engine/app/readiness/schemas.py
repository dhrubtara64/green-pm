"""Domain schemas and Pydantic API schemas for the Readiness Engine — S10-01–S10-05."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GATE_TYPES: tuple[str, ...] = (
    "ENGINEERING",
    "MATERIAL",
    "CONSTRUCTION",
    "QUALITY",
    "COMMISSIONING",
    "COD",
)

_GATE_STATUSES: frozenset[str] = frozenset(
    {"NOT_STARTED", "IN_PROGRESS", "READY", "BLOCKED"}
)

_CRITERIA_STATUSES: frozenset[str] = frozenset({"PENDING", "MET", "WAIVED"})

GateType = Literal[
    "ENGINEERING", "MATERIAL", "CONSTRUCTION", "QUALITY", "COMMISSIONING", "COD"
]
GateStatus = Literal["NOT_STARTED", "IN_PROGRESS", "READY", "BLOCKED"]
CriterionStatus = Literal["PENDING", "MET", "WAIVED"]


# ---------------------------------------------------------------------------
# Frozen domain objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateComputationResult:
    """Computed readiness outcome for a single gate."""

    gate_type: str
    total_criteria: int
    met_criteria: int
    waived_criteria: int
    pending_criteria: int
    completion_percentage: float
    status: str

    def __post_init__(self) -> None:
        if self.gate_type not in _GATE_TYPES:
            raise ValueError(f"Unknown gate_type: {self.gate_type!r}")
        if self.status not in _GATE_STATUSES:
            raise ValueError(f"Unknown gate status: {self.status!r}")
        if not (0.0 <= self.completion_percentage <= 100.0):
            raise ValueError(
                f"completion_percentage must be in [0, 100], got {self.completion_percentage}"
            )


# ---------------------------------------------------------------------------
# Pydantic API schemas — Readiness Gate
# ---------------------------------------------------------------------------


class ReadinessGateCreate(BaseModel):
    project_id: uuid.UUID
    gate_type: GateType


class ReadinessGateResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    gate_type: str
    status: str
    completion_percentage: float
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pydantic API schemas — Readiness Criterion
# ---------------------------------------------------------------------------


class ReadinessCriterionCreate(BaseModel):
    gate_id: uuid.UUID
    gate_type: GateType
    title: str
    description: Optional[str] = None
    responsible_party: Optional[str] = None
    due_date: Optional[date] = None


class ReadinessCriterionResponse(BaseModel):
    id: uuid.UUID
    gate_id: uuid.UUID
    gate_type: str
    title: str
    description: Optional[str] = None
    responsible_party: Optional[str] = None
    due_date: Optional[date] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CriterionStatusUpdate(BaseModel):
    status: CriterionStatus


# ---------------------------------------------------------------------------
# Pydantic API schemas — Readiness Score
# ---------------------------------------------------------------------------


class ReadinessScoreResponse(BaseModel):
    id: uuid.UUID
    gate_id: uuid.UUID
    gate_type: str
    total_criteria: int
    met_criteria: int
    waived_criteria: int
    completion_percentage: float
    computed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
