"""PIG BFS traversal for cascade impact computation — S5-01."""
from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.graph import GraphEdge, GraphNode

_CASCADE_EDGE_TYPES = frozenset({"BLOCKS", "IMPACTS", "TRIGGERS", "DEPENDS_ON"})
_CACHE_TTL_SECONDS = 60.0

_TRAVERSAL_CACHE: dict[str, tuple["TraversalResult", float]] = {}


@dataclass(frozen=True)
class TraversalResult:
    start_entity_type: str
    start_entity_id: uuid.UUID
    affected_nodes: tuple
    edges_traversed: tuple
    hops_reached: int

    @property
    def affected_entity_ids(self) -> list[uuid.UUID]:
        return [n.entity_id for n in self.affected_nodes]


def _cache_key(
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    start_entity_type: str,
    start_entity_id: uuid.UUID,
    max_hops: int,
) -> str:
    return f"{tenant_id}:{project_id}:{start_entity_type}:{start_entity_id}:{max_hops}"


def clear_cache() -> None:
    """Clear the traversal cache — used in tests to ensure isolation."""
    _TRAVERSAL_CACHE.clear()


async def _find_node(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
) -> Optional[GraphNode]:
    return await session.scalar(
        select(GraphNode).where(
            and_(
                GraphNode.tenant_id == tenant_id,
                GraphNode.project_id == project_id,
                GraphNode.entity_type == entity_type,
                GraphNode.entity_id == entity_id,
            )
        )
    )


async def _find_node_by_id(
    session: AsyncSession,
    node_id: uuid.UUID,
) -> Optional[GraphNode]:
    return await session.scalar(
        select(GraphNode).where(GraphNode.id == node_id)
    )


async def _find_outgoing_edges(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    node_id: uuid.UUID,
) -> list[GraphEdge]:
    result = await session.execute(
        select(GraphEdge).where(
            and_(
                GraphEdge.tenant_id == tenant_id,
                GraphEdge.project_id == project_id,
                GraphEdge.source_node_id == node_id,
                GraphEdge.edge_type.in_(sorted(_CASCADE_EDGE_TYPES)),
            )
        )
    )
    return list(result.scalars().all())


async def traverse_impact(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    start_entity_type: str,
    start_entity_id: uuid.UUID,
    max_hops: int = 5,
) -> TraversalResult:
    """BFS traversal over cascade edges from a start entity.

    Cascade edge types: BLOCKS, IMPACTS, TRIGGERS, DEPENDS_ON.
    Results cached for 60 seconds per (tenant, project, start, max_hops).
    Returns an empty TraversalResult if the start node is not in PIG.
    """
    key = _cache_key(tenant_id, project_id, start_entity_type, start_entity_id, max_hops)
    now = time.monotonic()
    if key in _TRAVERSAL_CACHE:
        cached_result, cached_at = _TRAVERSAL_CACHE[key]
        if now - cached_at < _CACHE_TTL_SECONDS:
            return cached_result

    start_node = await _find_node(
        session, tenant_id, project_id, start_entity_type, start_entity_id
    )
    if start_node is None:
        result = TraversalResult(
            start_entity_type=start_entity_type,
            start_entity_id=start_entity_id,
            affected_nodes=(),
            edges_traversed=(),
            hops_reached=0,
        )
        _TRAVERSAL_CACHE[key] = (result, now)
        return result

    visited_ids: set[uuid.UUID] = {start_node.id}
    queue: deque[tuple[GraphNode, int]] = deque([(start_node, 0)])
    affected: list[GraphNode] = []
    edges: list[GraphEdge] = []
    max_hop_reached = 0

    while queue:
        node, depth = queue.popleft()
        if depth >= max_hops:
            continue
        outgoing = await _find_outgoing_edges(session, tenant_id, project_id, node.id)
        for edge in outgoing:
            edges.append(edge)
            target = await _find_node_by_id(session, edge.target_node_id)
            if target is None or target.id in visited_ids:
                continue
            visited_ids.add(target.id)
            affected.append(target)
            hop = depth + 1
            max_hop_reached = max(max_hop_reached, hop)
            queue.append((target, hop))

    result = TraversalResult(
        start_entity_type=start_entity_type,
        start_entity_id=start_entity_id,
        affected_nodes=tuple(affected),
        edges_traversed=tuple(edges),
        hops_reached=max_hop_reached,
    )
    _TRAVERSAL_CACHE[key] = (result, now)
    return result
