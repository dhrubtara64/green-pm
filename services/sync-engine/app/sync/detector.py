"""Synchronization & Consistency Engine — contradiction detector — S15-06."""
from __future__ import annotations

from typing import Any

from app.sync.schemas import INCONSISTENCY_THRESHOLD, InconsistencyResult


def _generate_recommendation(edge_type: str, delta: float, weight_a: float, weight_b: float) -> str:
    direction = "higher" if weight_b > weight_a else "lower"
    return (
        f"Inconsistency in '{edge_type}' edge: weight diverged from "
        f"{weight_a:.3f} to {weight_b:.3f} (delta={delta:.3f}). "
        f"Review the {direction}-weight source and reconcile with project baseline."
    )


def detect_contradictions(
    edges: list[dict[str, Any]],
    threshold: float = INCONSISTENCY_THRESHOLD,
) -> list[InconsistencyResult]:
    groups: dict[tuple, list[float]] = {}
    first_edge: dict[tuple, dict] = {}

    for edge in edges:
        a = edge.get("entity_a_id")
        b = edge.get("entity_b_id")
        edge_type = edge.get("edge_type", "")
        if a is None or b is None:
            continue
        weight = float(edge.get("weight", 0.0))
        key = (a, b, edge_type)
        if key not in groups:
            groups[key] = []
            first_edge[key] = edge
        groups[key].append(weight)

    results: list[InconsistencyResult] = []
    for (a, b, edge_type), weights in groups.items():
        if len(weights) < 2:
            continue
        w_min = min(weights)
        w_max = max(weights)
        delta = w_max - w_min
        if delta <= threshold:
            continue
        results.append(
            InconsistencyResult(
                entity_a_id=a,
                entity_b_id=b,
                edge_type=edge_type,
                weight_a=w_min,
                weight_b=w_max,
                delta=delta,
                recommendation=_generate_recommendation(edge_type, delta, w_min, w_max),
            )
        )

    return sorted(results, key=lambda r: -r.delta)
