"""CPM service — fetches PIG data, runs CPM computation, persists results."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select

from shared.models.graph import GraphEdge, GraphNode
from shared.outbox.writer import write_outbox_event
from app.cpm.algorithm import compute_cpm
from app.cpm.model import CriticalPathResult
from app.cpm.schemas import CPMEdge, CPMNode, _DEPENDENCY_TYPES


class CPMNotFoundError(Exception):
    pass


async def _fetch_cpm_data(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> tuple[list[CPMNode], list[CPMEdge]]:
    """Fetch activity nodes and dependency edges from the PIG for a project."""
    result = await session.execute(
        select(GraphNode).where(
            and_(
                GraphNode.tenant_id == tenant_id,
                GraphNode.project_id == project_id,
                GraphNode.entity_type == "activity",
            )
        )
    )
    graph_nodes = result.scalars().all()

    node_id_to_entity: dict[uuid.UUID, uuid.UUID] = {}
    cpm_nodes: list[CPMNode] = []
    node_ids: set[uuid.UUID] = set()

    for n in graph_nodes:
        attrs = n.attributes or {}
        duration = max(0.0, float(attrs.get("duration_days", 0.0)))
        cpm_nodes.append(CPMNode(entity_id=n.entity_id, node_id=n.id, duration=duration))
        node_id_to_entity[n.id] = n.entity_id
        node_ids.add(n.id)

    if not node_ids:
        return cpm_nodes, []

    result = await session.execute(
        select(GraphEdge).where(
            and_(
                GraphEdge.tenant_id == tenant_id,
                GraphEdge.project_id == project_id,
                GraphEdge.edge_type.in_(["BLOCKS", "DEPENDS_ON"]),
                GraphEdge.source_node_id.in_(node_ids),
                GraphEdge.target_node_id.in_(node_ids),
            )
        )
    )
    graph_edges = result.scalars().all()

    cpm_edges: list[CPMEdge] = []
    for e in graph_edges:
        src_entity = node_id_to_entity.get(e.source_node_id)
        tgt_entity = node_id_to_entity.get(e.target_node_id)
        if src_entity is None or tgt_entity is None:
            continue
        attrs = e.edge_attributes or {}
        dep_type = attrs.get("dep_type", "FS")
        if dep_type not in _DEPENDENCY_TYPES:
            dep_type = "FS"
        lag = float(getattr(e, "weight", 0.0) or 0.0)
        cpm_edges.append(
            CPMEdge(
                source_entity_id=src_entity,
                target_entity_id=tgt_entity,
                dep_type=dep_type,
                lag=lag,
            )
        )

    return cpm_nodes, cpm_edges


async def run_cpm_for_project(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> CriticalPathResult:
    """Fetch PIG activity graph, compute CPM, persist and return the result."""
    nodes, edges = await _fetch_cpm_data(session, tenant_id, project_id)
    cpm_result = compute_cpm(nodes, edges)
    as_dict = cpm_result.as_dict()

    record = CriticalPathResult(
        id=uuid.uuid4(),
        project_id=project_id,
        tenant_id=tenant_id,
        project_duration=cpm_result.project_duration,
        critical_path_activity_ids=as_dict["critical_path"],
        near_critical_activity_ids=as_dict["near_critical"],
        activity_floats=as_dict["activity_floats"],
        status="computed",
        computed_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def get_latest_cpm_result(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Optional[CriticalPathResult]:
    """Return the most recent computed CPM result for a project, or None."""
    return await session.scalar(
        select(CriticalPathResult)
        .where(
            and_(
                CriticalPathResult.project_id == project_id,
                CriticalPathResult.tenant_id == tenant_id,
                CriticalPathResult.status == "computed",
            )
        )
        .order_by(CriticalPathResult.computed_at.desc())
        .limit(1)
    )


async def get_activity_float_info(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> Optional[dict]:
    """Return float info dict for a specific activity from the latest CPM result."""
    result = await get_latest_cpm_result(session, tenant_id, project_id)
    if result is None:
        return None
    return result.activity_floats.get(str(activity_id))
