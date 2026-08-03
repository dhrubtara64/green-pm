"""Perturbation application engine — S11-03."""
from __future__ import annotations

from app.simulation.schemas import PerturbationSpec


class NodeNotFoundError(Exception):
    pass


def apply_perturbation(snapshot: dict, spec: PerturbationSpec) -> dict:
    """Return a new snapshot with spec applied to the matching node.

    The input snapshot is never mutated.
    Raises NodeNotFoundError when spec.node_ref is absent from the snapshot.
    """
    new_nodes = []
    applied = False
    for node in snapshot.get("nodes", []):
        if node["node_ref"] == spec.node_ref:
            new_nodes.append({**node, spec.field: spec.perturbed_value})
            applied = True
        else:
            new_nodes.append(node)

    if not applied:
        raise NodeNotFoundError(
            f"Node {spec.node_ref!r} not found in snapshot"
        )

    return {**snapshot, "nodes": new_nodes}


def apply_all_perturbations(snapshot: dict, specs: list[PerturbationSpec]) -> dict:
    """Apply specs in order, threading the result through each application."""
    result = snapshot
    for spec in specs:
        result = apply_perturbation(result, spec)
    return result
