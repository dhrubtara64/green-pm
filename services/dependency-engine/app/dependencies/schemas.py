"""Pydantic schemas for the /activities/{id}/dependencies API endpoint."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ActivityDependencyInfo(BaseModel):
    """Float and dependency graph info for a single activity."""
    activity_id: uuid.UUID
    early_start: float
    early_finish: float
    late_start: float
    late_finish: float
    total_float: float
    free_float: float
    is_critical: bool
    predecessors: list[str]  # str(UUID) of predecessor activity_ids
    successors: list[str]    # str(UUID) of successor activity_ids

    model_config = {"from_attributes": True}


class DependencyGraphResponse(BaseModel):
    """Full dependency graph response for a project's CPM computation."""
    project_id: uuid.UUID
    computed_at: datetime
    project_duration: float
    critical_path: list[str]   # ordered list of str(UUID)
    near_critical: list[str]   # activities with 0 < TF < 2 days
    activities: list[ActivityDependencyInfo]

    model_config = {"from_attributes": True}

    @classmethod
    def from_cpm_result(
        cls,
        project_id: uuid.UUID,
        computed_at: datetime,
        project_duration: float,
        critical_path: list[str],
        near_critical: list[str],
        activity_floats: dict[str, dict],
        predecessors_map: dict[str, list[str]],
        successors_map: dict[str, list[str]],
    ) -> "DependencyGraphResponse":
        activities = []
        for aid_str, floats in activity_floats.items():
            activities.append(
                ActivityDependencyInfo(
                    activity_id=uuid.UUID(aid_str),
                    early_start=floats["early_start"],
                    early_finish=floats["early_finish"],
                    late_start=floats["late_start"],
                    late_finish=floats["late_finish"],
                    total_float=floats["total_float"],
                    free_float=floats["free_float"],
                    is_critical=floats["is_critical"],
                    predecessors=predecessors_map.get(aid_str, []),
                    successors=successors_map.get(aid_str, []),
                )
            )
        return cls(
            project_id=project_id,
            computed_at=computed_at,
            project_duration=project_duration,
            critical_path=critical_path,
            near_critical=near_critical,
            activities=activities,
        )
