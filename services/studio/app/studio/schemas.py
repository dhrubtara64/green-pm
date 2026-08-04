"""Domain schemas for Green PM Studio — S18-01."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

BUILDER_TYPES: frozenset[str] = frozenset({
    "WBS_TEMPLATE",
    "ACTIVITY_TEMPLATE",
    "EVIDENCE_SCORING",
    "VENDOR_SCORECARD",
    "RISK_MATRIX",
    "DISPATCH_TEMPLATE",
    "CHANGE_CATEGORY",
    "READINESS_GATE",
    "SIMULATION_SCENARIO",
    "COORDINATION_TEMPLATE",
    "MEMORY_PATTERN",
    "FORECAST_MODEL",
    "ALIGNMENT_PROFILE",
    "DECISION_MATRIX",
    "SYNC_POLICY",
})

BUILDER_COUNT: int = 15

_ENGINE_MAP: dict[str, str] = {
    "WBS_TEMPLATE": "core-platform",
    "ACTIVITY_TEMPLATE": "core-platform",
    "EVIDENCE_SCORING": "evidence-engine",
    "VENDOR_SCORECARD": "vendor-engine",
    "RISK_MATRIX": "risk-engine",
    "DISPATCH_TEMPLATE": "supply-chain-engine",
    "CHANGE_CATEGORY": "impact-engine",
    "READINESS_GATE": "readiness-engine",
    "SIMULATION_SCENARIO": "simulation-engine",
    "COORDINATION_TEMPLATE": "coordination-engine",
    "MEMORY_PATTERN": "organizational-memory",
    "FORECAST_MODEL": "forecasting-engine",
    "ALIGNMENT_PROFILE": "alignment-engine",
    "DECISION_MATRIX": "decision-engine",
    "SYNC_POLICY": "sync-engine",
}


@dataclass(frozen=True)
class BuilderConfig:
    builder_type: str
    name: str
    config_data: dict

    def __post_init__(self) -> None:
        if self.builder_type not in BUILDER_TYPES:
            raise ValueError(
                f"Unknown builder_type '{self.builder_type}'. "
                f"Must be one of: {sorted(BUILDER_TYPES)}"
            )
        if not self.name or not self.name.strip():
            raise ValueError("BuilderConfig.name must be non-empty")

    @property
    def target_engine(self) -> str:
        return _ENGINE_MAP[self.builder_type]


class BuilderCreate(BaseModel):
    project_id: uuid.UUID
    builder_type: str
    name: str
    config_data: dict = {}
    description: Optional[str] = None

    @field_validator("builder_type")
    @classmethod
    def validate_builder_type(cls, v: str) -> str:
        if v not in BUILDER_TYPES:
            raise ValueError(f"Invalid builder_type '{v}'")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must be non-empty")
        return v


class BuilderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    builder_type: str
    name: str
    config_data: dict = {}
    description: Optional[str] = None
    is_active: bool = True


def target_engine_for(builder_type: str) -> str:
    if builder_type not in BUILDER_TYPES:
        raise ValueError(f"Unknown builder_type: '{builder_type}'")
    return _ENGINE_MAP[builder_type]
