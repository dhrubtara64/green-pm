"""Synchronization & Consistency Engine value objects and API schemas — S15-06."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

INCONSISTENCY_THRESHOLD: float = 0.2


@dataclass(frozen=True)
class InconsistencyResult:
    entity_a_id: uuid.UUID
    entity_b_id: uuid.UUID
    edge_type: str
    weight_a: float
    weight_b: float
    delta: float
    recommendation: str


class SyncEdge(BaseModel):
    entity_a_id: uuid.UUID
    entity_b_id: uuid.UUID
    edge_type: str
    weight: float
    source: Optional[str] = None

    @field_validator("edge_type")
    @classmethod
    def edge_type_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("edge_type must not be empty")
        return v


class SyncCheckCreate(BaseModel):
    project_id: uuid.UUID
    edges: list[SyncEdge]


class InconsistencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity_a_id: uuid.UUID
    entity_b_id: uuid.UUID
    edge_type: str
    weight_a: float
    weight_b: float
    delta: float
    recommendation: str
    flagged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class ConsistencyReportResponse(BaseModel):
    project_id: uuid.UUID
    total_edges_checked: int
    inconsistencies_found: int
    inconsistencies: list[InconsistencyResponse]
