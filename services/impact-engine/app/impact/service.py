"""Impact quantification and narrative generation — S5-02, S5-04."""
from __future__ import annotations

import uuid

from .schemas import ImpactDimension, ImpactResult
from ..traversal.pig_traversal import TraversalResult

_QUALITY_ENTITY_TYPES = frozenset({"evidence", "inspection", "gate"})
_SAFETY_ENTITY_TYPES = frozenset({"inspection", "commissioning_item"})
_REGULATORY_ENTITY_TYPES = frozenset({"gate", "document", "drawing"})


def quantify_impact(traversal: TraversalResult) -> ImpactResult:
    """Compute 6-dimension impact from a PIG traversal result.

    All 6 dimensions are always present; zero-impact dimensions carry value=0.0
    and confidence_score=0.0, satisfying the acceptance criterion that zero-impact
    dimensions are included with zero values.
    """
    affected = traversal.affected_nodes
    edges = traversal.edges_traversed

    scope_value = float(len(affected))
    schedule_value = sum(
        float(getattr(e, "weight", 1.0)) for e in edges if e.edge_type == "BLOCKS"
    )
    total_weight = sum(float(getattr(e, "weight", 1.0)) for e in edges)
    avg_weight = total_weight / len(edges) if edges else 0.0
    cost_value = round(scope_value * avg_weight, 4)

    quality_count = float(
        sum(1 for n in affected if n.entity_type in _QUALITY_ENTITY_TYPES)
    )
    safety_count = float(
        sum(1 for n in affected if n.entity_type in _SAFETY_ENTITY_TYPES)
    )
    regulatory_count = float(
        sum(1 for n in affected if n.entity_type in _REGULATORY_ENTITY_TYPES)
    )

    dimensions = {
        "scope": ImpactDimension(
            "scope", scope_value, "node_count",
            min(1.0, scope_value / 10.0) if scope_value > 0 else 0.0,
        ),
        "schedule": ImpactDimension(
            "schedule", schedule_value, "days",
            0.8 if schedule_value > 0 else 0.0,
        ),
        "cost": ImpactDimension(
            "cost", cost_value, "score",
            0.7 if cost_value > 0 else 0.0,
        ),
        "quality": ImpactDimension(
            "quality", quality_count, "node_count",
            0.6 if quality_count > 0 else 0.0,
        ),
        "safety": ImpactDimension(
            "safety", safety_count, "node_count",
            0.9 if safety_count > 0 else 0.0,
        ),
        "regulatory": ImpactDimension(
            "regulatory", regulatory_count, "node_count",
            0.7 if regulatory_count > 0 else 0.0,
        ),
    }

    edge_dicts = tuple(
        {
            "source_node_id": str(e.source_node_id),
            "target_node_id": str(e.target_node_id),
            "edge_type": e.edge_type,
            "weight": float(getattr(e, "weight", 1.0)),
        }
        for e in edges
    )

    narrative = _generate_narrative(
        start_entity_type=traversal.start_entity_type,
        start_entity_id=traversal.start_entity_id,
        affected_count=len(affected),
        hops=traversal.hops_reached,
        dimensions=dimensions,
    )

    return ImpactResult(
        dimensions=dimensions,
        affected_entity_count=len(affected),
        impact_graph_edges=edge_dicts,
        narrative_summary=narrative,
    )


def _generate_narrative(
    *,
    start_entity_type: str,
    start_entity_id: uuid.UUID,
    affected_count: int,
    hops: int,
    dimensions: dict[str, ImpactDimension],
) -> str:
    if affected_count == 0:
        return (
            f"The change to {start_entity_type} {start_entity_id} "
            "has no cascading impact on other project entities at this time."
        )

    entity_word = "entity" if affected_count == 1 else "entities"
    hop_word = "hop" if hops == 1 else "hops"
    parts = [
        f"The change to {start_entity_type} {start_entity_id} "
        f"cascades to {affected_count} project {entity_word} "
        f"within {hops} {hop_word} of the PIG."
    ]

    schedule = dimensions["schedule"]
    if schedule.value > 0:
        parts.append(
            f"Schedule impact: {schedule.value:.1f} day(s) of potential delay "
            f"(confidence {schedule.confidence_score:.0%})."
        )

    safety = dimensions["safety"]
    if safety.value > 0:
        parts.append(
            f"Safety-critical entities affected: {int(safety.value)}. "
            "Review required before proceeding."
        )

    regulatory = dimensions["regulatory"]
    if regulatory.value > 0:
        parts.append(
            f"Regulatory gate or document entities affected: {int(regulatory.value)}. "
            "Compliance check recommended."
        )

    return " ".join(parts)
