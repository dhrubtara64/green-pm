"""Schemas for material readiness and critical material results."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialReadinessResult:
    """Readiness score for a dispatch at a given stage."""
    stage: str
    stage_index: int
    score: float           # 0.0–100.0
    critical_item_count: int
    total_item_count: int


@dataclass(frozen=True)
class CriticalMaterialInfo:
    """A material item flagged as critical because its activity is on the critical path."""
    material_item_id: uuid.UUID
    activity_id: uuid.UUID
    description: str
