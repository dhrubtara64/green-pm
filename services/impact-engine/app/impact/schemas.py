"""Impact dimension value objects — S5-02."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_IMPACT_DIMENSIONS = frozenset({
    "scope", "schedule", "cost", "quality", "safety", "regulatory",
})


@dataclass(frozen=True)
class ImpactDimension:
    dimension: str
    value: float
    unit: str
    confidence_score: float


@dataclass(frozen=True)
class ImpactResult:
    dimensions: dict[str, ImpactDimension]
    affected_entity_count: int
    impact_graph_edges: tuple[dict[str, Any], ...]
    narrative_summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimensions": {
                k: {
                    "dimension": v.dimension,
                    "value": v.value,
                    "unit": v.unit,
                    "confidence_score": v.confidence_score,
                }
                for k, v in self.dimensions.items()
            },
            "affected_entity_count": self.affected_entity_count,
            "impact_graph_edges": list(self.impact_graph_edges),
            "narrative_summary": self.narrative_summary,
        }
