"""Organizational Memory Engine schemas — S13-01, S13-05, S13-06."""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

_MEMORY_CATEGORIES: frozenset[str] = frozenset({"DECISION", "VENDOR", "RISK", "SCHEDULE"})


@dataclass(frozen=True)
class MemorySearchQuery:
    category: str
    context_keywords: tuple[str, ...]
    top_k: int = 5

    def __post_init__(self) -> None:
        if self.category not in _MEMORY_CATEGORIES:
            raise ValueError(f"category must be one of {_MEMORY_CATEGORIES}, got {self.category!r}")
        if self.top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {self.top_k}")


@dataclass(frozen=True)
class PatternMatch:
    pattern_id: uuid.UUID
    pattern_name: str
    category: str
    confidence_score: float
    historical_outcomes: tuple
    relevance_score: float


class MemoryRecordCreate(BaseModel):
    project_id: uuid.UUID
    category: str
    summary: str
    entity_id: Optional[uuid.UUID] = None
    entity_type: Optional[str] = None
    context: Optional[dict] = None
    confidence_score: float = 0.5
    outcome: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in _MEMORY_CATEGORIES:
            raise ValueError(f"category must be one of {_MEMORY_CATEGORIES}")
        return v

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be in [0.0, 1.0]")
        return v


class MemoryRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    category: str
    summary: str
    entity_id: Optional[uuid.UUID] = None
    entity_type: Optional[str] = None
    context: Optional[dict] = None
    confidence_score: float
    outcome: Optional[str] = None
    created_at: Optional[datetime] = None


class MemoryPatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    category: str
    pattern_name: str
    trigger_conditions: Optional[dict] = None
    historical_outcomes: Optional[list] = None
    confidence_score: float
    occurrence_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemorySearchRequest(BaseModel):
    category: str
    context_keywords: list[str]
    top_k: int = 5

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in _MEMORY_CATEGORIES:
            raise ValueError(f"category must be one of {_MEMORY_CATEGORIES}")
        return v

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v < 1:
            raise ValueError("top_k must be >= 1")
        return v


class HistoricalContextResponse(BaseModel):
    pattern_name: str
    category: str
    confidence_score: float
    historical_outcomes: list
    relevance_score: float


class MemorySearchResponse(BaseModel):
    matches: list[HistoricalContextResponse]
    total: int
