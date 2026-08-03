"""Domain and API schemas for the Simulation Engine — S11-01, S11-05."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

_SCENARIO_STATUSES: frozenset[str] = frozenset({"DRAFT", "ACTIVE", "ARCHIVED"})

_PERTURBATION_FIELDS: frozenset[str] = frozenset(
    {"duration_days", "cost_estimate", "completion_pct"}
)

PerturbationField = Literal["duration_days", "cost_estimate", "completion_pct"]


@dataclass(frozen=True)
class PerturbationSpec:
    node_ref: str
    field: str
    original_value: float
    perturbed_value: float

    def __post_init__(self) -> None:
        if not self.node_ref:
            raise ValueError("node_ref must not be empty")
        if self.field not in _PERTURBATION_FIELDS:
            raise ValueError(
                f"field {self.field!r} not in allowed perturbation fields"
            )


@dataclass(frozen=True)
class ProjectionResult:
    scenario_id: uuid.UUID
    schedule_delta_days: float
    budget_delta_pct: float
    affected_node_count: int
    critical_path_affected: bool

    def __post_init__(self) -> None:
        if self.affected_node_count < 0:
            raise ValueError("affected_node_count must be >= 0")


# ---------------------------------------------------------------------------
# Pydantic API schemas
# ---------------------------------------------------------------------------

class ScenarioCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class PerturbationCreate(BaseModel):
    node_ref: str
    field: PerturbationField
    original_value: float
    perturbed_value: float


class ScenarioPerturbationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    node_ref: str
    field: str
    original_value: float
    perturbed_value: float


class ScenarioProjectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    schedule_delta_days: float
    budget_delta_pct: float
    critical_path_changes: Optional[dict] = None
    projected_at: Optional[datetime] = None
