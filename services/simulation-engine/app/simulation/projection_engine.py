"""Forward projection engine — S11-04."""
from __future__ import annotations

import uuid

from app.simulation.schemas import ProjectionResult


def project_impacts(
    scenario_id: uuid.UUID,
    baseline: dict,
    perturbed: dict,
) -> ProjectionResult:
    """Compute schedule delta, budget delta, and critical-path impact.

    Compares node-by-node between baseline and perturbed snapshots.
    Nodes absent from perturbed are treated as unchanged.

    schedule_delta_days > 0 means delay; < 0 means acceleration.
    budget_delta_pct > 0 means cost overrun; < 0 means saving.
    critical_path_affected is True when any affected node has completion_pct < 100.
    """
    baseline_nodes = {n["node_ref"]: n for n in baseline.get("nodes", [])}
    perturbed_nodes = {n["node_ref"]: n for n in perturbed.get("nodes", [])}

    total_baseline_duration = 0.0
    total_perturbed_duration = 0.0
    total_baseline_cost = 0.0
    total_perturbed_cost = 0.0
    affected_refs: list[str] = []

    for ref, b_node in baseline_nodes.items():
        p_node = perturbed_nodes.get(ref, b_node)

        b_dur = b_node.get("duration_days", 0.0)
        p_dur = p_node.get("duration_days", b_dur)
        b_cost = b_node.get("cost_estimate", 0.0)
        p_cost = p_node.get("cost_estimate", b_cost)

        total_baseline_duration += b_dur
        total_perturbed_duration += p_dur
        total_baseline_cost += b_cost
        total_perturbed_cost += p_cost

        if b_dur != p_dur or b_cost != p_cost:
            affected_refs.append(ref)

    schedule_delta = round(total_perturbed_duration - total_baseline_duration, 2)

    if total_baseline_cost > 0:
        budget_delta_pct = round(
            (total_perturbed_cost - total_baseline_cost) / total_baseline_cost * 100,
            4,
        )
    else:
        budget_delta_pct = 0.0

    critical_path_affected = any(
        baseline_nodes[ref].get("completion_pct", 100.0) < 100.0
        for ref in affected_refs
        if ref in baseline_nodes
    )

    return ProjectionResult(
        scenario_id=scenario_id,
        schedule_delta_days=schedule_delta,
        budget_delta_pct=budget_delta_pct,
        affected_node_count=len(affected_refs),
        critical_path_affected=critical_path_affected,
    )
