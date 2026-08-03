"""Pydantic schemas for Change and ImpactAssessment — S5-05."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

_CHANGE_TYPES = frozenset({
    "scope_change", "schedule_change", "cost_change", "design_change",
    "supplier_change", "workforce_change", "resource_change", "risk_escalation",
})

_CHANGE_STATUSES = frozenset({
    "initiated", "assessing", "assessed", "approved", "rejected", "withdrawn",
})


class ChangeCreate(BaseModel):
    project_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    change_type: str
    description: Optional[str] = Field(None, max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_change_type(self) -> "ChangeCreate":
        if self.change_type not in _CHANGE_TYPES:
            raise ValueError(
                f"Invalid change_type: {self.change_type!r}. "
                f"Must be one of {sorted(_CHANGE_TYPES)}"
            )
        return self


class ChangeResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    change_type: str
    description: Optional[str] = None
    status: str
    metadata: dict[str, Any] = Field(validation_alias="change_metadata")
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ImpactAssessmentResponse(BaseModel):
    id: uuid.UUID
    change_id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    status: str
    dimensions: dict[str, Any]
    affected_entity_ids: list[str]
    impact_graph_edges: list[dict[str, Any]]
    narrative_summary: Optional[str] = None
    computed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
