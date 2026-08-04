"""Domain schemas for the AI Orchestration Engine — S16-02, S16-03, S16-04."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

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

_MAX_ENGINES: int = 16
_MIN_ENGINES: int = 1


@dataclass(frozen=True)
class AIQuery:
    """Pure value object representing an NL query to the orchestration layer."""

    project_id: uuid.UUID
    query_text: str
    max_engines: int = 5

    def __post_init__(self) -> None:
        if not self.query_text.strip():
            raise ValueError("query_text cannot be empty")
        if not (_MIN_ENGINES <= self.max_engines <= _MAX_ENGINES):
            raise ValueError(
                f"max_engines must be between {_MIN_ENGINES} and {_MAX_ENGINES}"
            )


@dataclass(frozen=True)
class EvidenceChain:
    """Immutable record of which PIG nodes and scores informed an AI response."""

    chain_id: uuid.UUID
    query_id: uuid.UUID
    pig_node_ids: frozenset
    scores_used: dict
    engines_consulted: frozenset
    created_at: datetime


class QueryRequest(BaseModel):
    project_id: uuid.UUID
    query_text: str
    max_engines: int = 5

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query_text cannot be empty")
        return v

    @field_validator("max_engines")
    @classmethod
    def validate_max_engines(cls, v: int) -> int:
        if not (_MIN_ENGINES <= v <= _MAX_ENGINES):
            raise ValueError(
                f"max_engines must be between {_MIN_ENGINES} and {_MAX_ENGINES}"
            )
        return v


class CopilotRequest(BaseModel):
    project_id: uuid.UUID
    query_text: str
    context: Optional[str] = None

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query_text cannot be empty")
        return v


class QueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query_id: uuid.UUID
    project_id: uuid.UUID
    response: str
    evidence_chain_id: uuid.UUID
    source_count: int


class CopilotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query_id: uuid.UUID
    project_id: uuid.UUID
    response: str
    evidence_chain_id: uuid.UUID


class EvidenceChainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    query_id: uuid.UUID
    pig_node_ids: list = []
    scores_used: dict = {}
    engines_consulted: list = []
    created_at: Optional[datetime] = None
