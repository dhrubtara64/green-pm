"""CPM algorithm — forward/backward pass with FS/SS/FF/SF dependency types."""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Sequence

from app.cpm.schemas import (
    ActivityFloat,
    CPMEdge,
    CPMNode,
    CPMResult,
    _NEAR_CRITICAL_THRESHOLD,
)


class CyclicDependencyError(Exception):
    """Raised when the activity dependency graph contains a cycle."""


def _topological_sort(
    entity_ids: list[uuid.UUID],
    edges: Sequence[CPMEdge],
) -> list[uuid.UUID]:
    """Kahn's algorithm. Raises CyclicDependencyError if a cycle is detected."""
    in_degree: dict[uuid.UUID, int] = {eid: 0 for eid in entity_ids}
    successors: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)

    for edge in edges:
        if edge.source_entity_id in in_degree and edge.target_entity_id in in_degree:
            successors[edge.source_entity_id].append(edge.target_entity_id)
            in_degree[edge.target_entity_id] += 1

    queue: deque[uuid.UUID] = deque(eid for eid, deg in in_degree.items() if deg == 0)
    sorted_ids: list[uuid.UUID] = []

    while queue:
        node = queue.popleft()
        sorted_ids.append(node)
        for succ in successors[node]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(sorted_ids) != len(entity_ids):
        raise CyclicDependencyError("Cycle detected in activity dependency graph")
    return sorted_ids


def compute_cpm(
    nodes: Sequence[CPMNode],
    edges: Sequence[CPMEdge],
) -> CPMResult:
    """Compute CPM over activity nodes using FS/SS/FF/SF dependency types with lag/lead.

    Returns CPMResult with project_duration=0.0 for an empty graph.
    Raises CyclicDependencyError if the graph contains a cycle.
    """
    if not nodes:
        return CPMResult(
            project_duration=0.0,
            critical_path=(),
            near_critical=(),
            floats={},
        )

    nodes_by_id: dict[uuid.UUID, CPMNode] = {n.entity_id: n for n in nodes}
    entity_ids = list(nodes_by_id.keys())

    valid_edges = [
        e for e in edges
        if e.source_entity_id in nodes_by_id and e.target_entity_id in nodes_by_id
    ]

    sorted_ids = _topological_sort(entity_ids, valid_edges)

    edges_by_target: dict[uuid.UUID, list[CPMEdge]] = defaultdict(list)
    edges_by_source: dict[uuid.UUID, list[CPMEdge]] = defaultdict(list)
    for e in valid_edges:
        edges_by_target[e.target_entity_id].append(e)
        edges_by_source[e.source_entity_id].append(e)

    # ── Forward pass ──────────────────────────────────────────────────────────
    es: dict[uuid.UUID, float] = {eid: 0.0 for eid in sorted_ids}
    ef: dict[uuid.UUID, float] = {}

    for eid in sorted_ids:
        node = nodes_by_id[eid]
        for edge in edges_by_target[eid]:
            src = edge.source_entity_id
            lag = edge.lag
            dep = edge.dep_type
            if dep == "FS":
                es[eid] = max(es[eid], ef.get(src, 0.0) + lag)
            elif dep == "SS":
                es[eid] = max(es[eid], es[src] + lag)
            elif dep == "FF":
                # EF[tgt] >= EF[src] + lag → ES[tgt] >= EF[src] + lag - dur[tgt]
                es[eid] = max(es[eid], ef.get(src, 0.0) + lag - node.duration)
            elif dep == "SF":
                # EF[tgt] >= ES[src] + lag → ES[tgt] >= ES[src] + lag - dur[tgt]
                es[eid] = max(es[eid], es[src] + lag - node.duration)
        es[eid] = max(0.0, es[eid])
        ef[eid] = es[eid] + node.duration

    project_duration = max(ef.values())

    # ── Backward pass ─────────────────────────────────────────────────────────
    lf: dict[uuid.UUID, float] = {eid: project_duration for eid in sorted_ids}

    for eid in reversed(sorted_ids):
        node = nodes_by_id[eid]
        for edge in edges_by_source[eid]:
            tgt = edge.target_entity_id
            lag = edge.lag
            dep = edge.dep_type
            dur_tgt = nodes_by_id[tgt].duration
            if dep == "FS":
                # LF[src] <= LS[tgt] - lag = (LF[tgt] - dur[tgt]) - lag
                lf[eid] = min(lf[eid], lf[tgt] - dur_tgt - lag)
            elif dep == "SS":
                # LS[src] <= LS[tgt] - lag → LF[src] <= LS[tgt] - lag + dur[src]
                ls_tgt = lf[tgt] - dur_tgt
                lf[eid] = min(lf[eid], ls_tgt - lag + node.duration)
            elif dep == "FF":
                # LF[src] <= LF[tgt] - lag
                lf[eid] = min(lf[eid], lf[tgt] - lag)
            elif dep == "SF":
                # LS[src] <= LF[tgt] - lag → LF[src] <= LF[tgt] - lag + dur[src]
                lf[eid] = min(lf[eid], lf[tgt] - lag + node.duration)

    ls: dict[uuid.UUID, float] = {eid: lf[eid] - nodes_by_id[eid].duration for eid in sorted_ids}

    # ── Free float ────────────────────────────────────────────────────────────
    free_float: dict[uuid.UUID, float] = {}
    for eid in sorted_ids:
        out_edges = edges_by_source[eid]
        if not out_edges:
            # Sink node: free float = slack to project end
            free_float[eid] = max(0.0, project_duration - ef[eid])
        else:
            ff_val = float("inf")
            for edge in out_edges:
                tgt = edge.target_entity_id
                lag = edge.lag
                dep = edge.dep_type
                if dep == "FS":
                    ff_val = min(ff_val, es[tgt] - ef[eid] - lag)
                elif dep == "SS":
                    ff_val = min(ff_val, es[tgt] - es[eid] - lag)
                elif dep in ("FF", "SF"):
                    ff_val = min(ff_val, 0.0)
            free_float[eid] = max(0.0, ff_val if ff_val != float("inf") else 0.0)

    # ── Assemble results ──────────────────────────────────────────────────────
    activity_floats: dict[uuid.UUID, ActivityFloat] = {}
    for eid in sorted_ids:
        tf = max(0.0, round(ls[eid] - es[eid], 6))
        is_crit = tf < 1e-6
        activity_floats[eid] = ActivityFloat(
            entity_id=eid,
            early_start=round(es[eid], 6),
            early_finish=round(ef[eid], 6),
            late_start=round(ls[eid], 6),
            late_finish=round(lf[eid], 6),
            total_float=tf,
            free_float=round(free_float[eid], 6),
            is_critical=is_crit,
        )

    critical_path = tuple(eid for eid in sorted_ids if activity_floats[eid].is_critical)
    near_critical = tuple(
        eid for eid in sorted_ids
        if not activity_floats[eid].is_critical
        and activity_floats[eid].total_float < _NEAR_CRITICAL_THRESHOLD
    )

    return CPMResult(
        project_duration=round(project_duration, 6),
        critical_path=critical_path,
        near_critical=near_critical,
        floats=activity_floats,
    )
