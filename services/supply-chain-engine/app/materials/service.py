"""Material readiness scoring and critical material identification — S7-03, S7-04."""
from __future__ import annotations

import uuid
from typing import Sequence

from app.dispatch.schemas import _DISPATCH_STAGES, _STAGE_INDEX, _CRITICALITY_WEIGHT
from app.materials.schemas import CriticalMaterialInfo, MaterialReadinessResult

_MAX_STAGE_INDEX = len(_DISPATCH_STAGES) - 1  # 9


def compute_readiness_score(
    stage: str,
    critical_item_count: int = 0,
    total_item_count: int = 0,
) -> float:
    """Return a readiness score 0.0–100.0 for the given dispatch stage.

    Base score comes from stage progress (index / max). When there are items,
    the effective progress is weighted: critical items count _CRITICALITY_WEIGHT × non-critical.
    A dispatch at the terminal stage (ACCEPTED) always returns 100.0.
    """
    idx = _STAGE_INDEX.get(stage, 0)
    base_progress = idx / _MAX_STAGE_INDEX  # 0.0 at stage 0, 1.0 at stage 9

    if total_item_count == 0:
        return round(base_progress * 100.0, 2)

    non_critical_count = total_item_count - critical_item_count
    effective_total = critical_item_count * _CRITICALITY_WEIGHT + non_critical_count
    effective_complete = (
        critical_item_count * _CRITICALITY_WEIGHT * base_progress
        + non_critical_count * base_progress
    )
    weighted_progress = effective_complete / effective_total if effective_total > 0 else base_progress
    return round(weighted_progress * 100.0, 2)


def build_readiness_result(
    stage: str,
    critical_item_count: int = 0,
    total_item_count: int = 0,
) -> MaterialReadinessResult:
    """Construct a MaterialReadinessResult for the given stage and item counts."""
    return MaterialReadinessResult(
        stage=stage,
        stage_index=_STAGE_INDEX.get(stage, 0),
        score=compute_readiness_score(stage, critical_item_count, total_item_count),
        critical_item_count=critical_item_count,
        total_item_count=total_item_count,
    )


def identify_critical_materials(
    material_items: Sequence,
    critical_activity_ids: set[uuid.UUID],
) -> list[CriticalMaterialInfo]:
    """Flag material items whose activity_id is in the CPM critical path.

    Returns a list of CriticalMaterialInfo for items that qualify.
    Items with no activity_id are never flagged.
    """
    results: list[CriticalMaterialInfo] = []
    for item in material_items:
        if item.activity_id is None:
            continue
        if uuid.UUID(str(item.activity_id)) in critical_activity_ids:
            results.append(
                CriticalMaterialInfo(
                    material_item_id=item.id,
                    activity_id=item.activity_id,
                    description=item.description,
                )
            )
    return results
