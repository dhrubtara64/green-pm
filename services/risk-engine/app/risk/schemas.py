"""Domain schemas and Pydantic API schemas for the Risk Engine — S9-01, S9-04, S9-05, S9-06."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RISK_STATUSES: frozenset[str] = frozenset({"OPEN", "MITIGATING", "CLOSED"})
_MITIGATION_STATUSES: frozenset[str] = frozenset({"OPEN", "IN_PROGRESS", "CLOSED"})


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskStatus(str, Enum):
    OPEN = "OPEN"
    MITIGATING = "MITIGATING"
    CLOSED = "CLOSED"


class MitigationStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


# ---------------------------------------------------------------------------
# Frozen domain objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeatMapCoordinates:
    """Probability × impact grid position for heat map rendering."""

    x: float  # probability axis
    y: float  # impact axis

    def __post_init__(self) -> None:
        for label, val in (("x", self.x), ("y", self.y)):
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"HeatMapCoordinates.{label} must be in [0, 1], got {val}")


@dataclass(frozen=True)
class RiskRegisterEntry:
    """Projection used by the risk register API response."""

    risk_id: uuid.UUID
    category: str
    description: str
    risk_score: float
    heat_map: HeatMapCoordinates
    status: str


@dataclass(frozen=True)
class RiskPatternMatch:
    """A historical pattern matched against the current risk."""

    pattern_id: uuid.UUID
    pattern_name: str
    confidence: float  # 0.0–1.0
    historical_outcome: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


# ---------------------------------------------------------------------------
# Pydantic API schemas — Risk
# ---------------------------------------------------------------------------


class RiskCreate(BaseModel):
    category: str
    description: str
    probability: float = Field(ge=0.0, le=1.0)
    impact: float = Field(ge=0.0, le=1.0)


class RiskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    category: str
    description: str
    probability: float
    impact: float
    risk_score: float
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pydantic API schemas — Risk Assessment
# ---------------------------------------------------------------------------


class RiskAssessmentCreate(BaseModel):
    notes: str
    schedule_base: float = Field(gt=0.0)
    schedule_std_dev: float = Field(ge=0.0)
    cost_base: float = Field(gt=0.0)
    cost_std_dev: float = Field(ge=0.0)


class RiskAssessmentResponse(BaseModel):
    id: uuid.UUID
    risk_id: uuid.UUID
    notes: str
    monte_carlo_result: dict
    assessed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pydantic API schemas — Risk Mitigation
# ---------------------------------------------------------------------------


class RiskMitigationCreate(BaseModel):
    action: str
    owner: str
    due_date: Optional[date] = None


class RiskMitigationResponse(BaseModel):
    id: uuid.UUID
    risk_id: uuid.UUID
    action: str
    owner: str
    due_date: Optional[date] = None
    status: str
    effectiveness_score: float
    outcome_verified: bool = False

    model_config = {"from_attributes": True}


class MitigationEffectivenessUpdate(BaseModel):
    effectiveness_score: float = Field(ge=0.0, le=1.0)
    status: Optional[str] = None
