from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from shared.models.graph import GRAPH_EDGE_TYPES, GRAPH_NODE_ENTITY_TYPES

_ENTITY_SET = frozenset(GRAPH_NODE_ENTITY_TYPES)
_EDGE_TYPE_SET = frozenset(GRAPH_EDGE_TYPES)


class NodeCreate(BaseModel):
    project_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("entity_type")
    @classmethod
    def valid_entity_type(cls, v: str) -> str:
        if v not in _ENTITY_SET:
            raise ValueError(f"Unknown entity_type: {v!r}. Must be one of {sorted(_ENTITY_SET)}")
        return v


class NodeUpdate(BaseModel):
    attributes: dict[str, Any]


class NodeResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    attributes: dict[str, Any]
    last_synced_at: datetime

    model_config = {"from_attributes": True}


class EdgeCreate(BaseModel):
    project_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    weight: float = Field(1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None

    @field_validator("edge_type")
    @classmethod
    def valid_edge_type(cls, v: str) -> str:
        if v not in _EDGE_TYPE_SET:
            raise ValueError(f"Unknown edge_type: {v!r}")
        return v


class EdgeResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    weight: float
    metadata_: dict[str, Any] = Field(alias="metadata_")
    expires_at: Optional[datetime]

    model_config = {"from_attributes": True, "populate_by_name": True}
