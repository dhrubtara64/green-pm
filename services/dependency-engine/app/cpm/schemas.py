"""CPM domain schemas — frozen dataclasses for immutable computation results."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

_DEPENDENCY_TYPES: frozenset[str] = frozenset({"FS", "SS", "FF", "SF"})
_NEAR_CRITICAL_THRESHOLD: float = 2.0  # days


@dataclass(frozen=True)
class CPMNode:
    """Activity node for CPM computation."""
    entity_id: uuid.UUID
    node_id: uuid.UUID
    duration: float  # days (>= 0)


@dataclass(frozen=True)
class CPMEdge:
    """Dependency edge between two activity nodes."""
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    dep_type: str  # "FS" | "SS" | "FF" | "SF"
    lag: float = 0.0  # days (negative = lead)


@dataclass(frozen=True)
class ActivityFloat:
    """CPM float values for a single activity."""
    entity_id: uuid.UUID
    early_start: float
    early_finish: float
    late_start: float
    late_finish: float
    total_float: float
    free_float: float
    is_critical: bool


@dataclass(frozen=True)
class CPMResult:
    """Result of a full CPM forward/backward pass computation."""
    project_duration: float
    critical_path: tuple[uuid.UUID, ...]  # ordered entity_ids on critical path
    near_critical: tuple[uuid.UUID, ...]  # float 0 < TF < threshold
    floats: dict[uuid.UUID, ActivityFloat]

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_duration": self.project_duration,
            "critical_path": [str(eid) for eid in self.critical_path],
            "near_critical": [str(eid) for eid in self.near_critical],
            "activity_floats": {
                str(eid): {
                    "early_start": af.early_start,
                    "early_finish": af.early_finish,
                    "late_start": af.late_start,
                    "late_finish": af.late_finish,
                    "total_float": af.total_float,
                    "free_float": af.free_float,
                    "is_critical": af.is_critical,
                }
                for eid, af in self.floats.items()
            },
        }
