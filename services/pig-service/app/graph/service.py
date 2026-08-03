from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.models.graph import GraphEdge, GraphNode

from .schemas import EdgeCreate, NodeCreate, NodeUpdate


class NodeNotFoundError(Exception):
    def __init__(self, node_id: uuid.UUID) -> None:
        super().__init__(f"GraphNode {node_id} not found")


class EdgeNotFoundError(Exception):
    def __init__(self, edge_id: uuid.UUID) -> None:
        super().__init__(f"GraphEdge {edge_id} not found")


class DuplicateNodeError(Exception):
    def __init__(self, project_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID) -> None:
        super().__init__(
            f"GraphNode already exists for {entity_type}/{entity_id} in project {project_id}"
        )


# ── Nodes ──────────────────────────────────────────────────────────────────────

async def upsert_node(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: NodeCreate,
) -> GraphNode:
    """Create or update the graph node for an entity (idempotent)."""
    now = datetime.now(timezone.utc)
    existing = await session.scalar(
        select(GraphNode).where(
            and_(
                GraphNode.project_id == data.project_id,
                GraphNode.entity_type == data.entity_type,
                GraphNode.entity_id == data.entity_id,
                GraphNode.tenant_id == tenant_id,
            )
        )
    )
    if existing is not None:
        existing.attributes = data.attributes
        existing.last_synced_at = now
        await session.flush()
        await session.refresh(existing)
        return existing

    node = GraphNode(
        id=uuid.uuid4(),
        project_id=data.project_id,
        tenant_id=tenant_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        attributes=data.attributes,
        last_synced_at=now,
    )
    session.add(node)
    await session.flush()
    await session.refresh(node)
    return node


async def get_node(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    node_id: uuid.UUID,
) -> GraphNode:
    node = await session.scalar(
        select(GraphNode).where(
            and_(GraphNode.id == node_id, GraphNode.tenant_id == tenant_id)
        )
    )
    if node is None:
        raise NodeNotFoundError(node_id)
    return node


async def get_node_by_entity(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
) -> Optional[GraphNode]:
    return await session.scalar(
        select(GraphNode).where(
            and_(
                GraphNode.project_id == project_id,
                GraphNode.entity_type == entity_type,
                GraphNode.entity_id == entity_id,
                GraphNode.tenant_id == tenant_id,
            )
        )
    )


async def list_nodes(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    entity_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[GraphNode]:
    q = (
        select(GraphNode)
        .where(and_(GraphNode.project_id == project_id, GraphNode.tenant_id == tenant_id))
        .order_by(GraphNode.last_synced_at.desc())
        .limit(limit).offset(offset)
    )
    if entity_type is not None:
        q = q.where(GraphNode.entity_type == entity_type)
    result = await session.execute(q)
    return result.scalars().all()


async def update_node_attributes(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    node_id: uuid.UUID,
    data: NodeUpdate,
) -> GraphNode:
    node = await get_node(session, tenant_id, node_id)
    node.attributes = {**node.attributes, **data.attributes}
    node.last_synced_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(node)
    return node


async def delete_node(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    node_id: uuid.UUID,
) -> None:
    node = await get_node(session, tenant_id, node_id)
    await session.delete(node)
    await session.flush()


# ── Edges ──────────────────────────────────────────────────────────────────────

async def create_edge(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    data: EdgeCreate,
) -> GraphEdge:
    edge = GraphEdge(
        id=uuid.uuid4(),
        project_id=data.project_id,
        tenant_id=tenant_id,
        source_node_id=data.source_node_id,
        target_node_id=data.target_node_id,
        edge_type=data.edge_type,
        weight=data.weight,
        metadata_=data.metadata,
        expires_at=data.expires_at,
    )
    session.add(edge)
    await session.flush()
    await session.refresh(edge)
    return edge


async def get_edge(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    edge_id: uuid.UUID,
) -> GraphEdge:
    edge = await session.scalar(
        select(GraphEdge).where(
            and_(GraphEdge.id == edge_id, GraphEdge.tenant_id == tenant_id)
        )
    )
    if edge is None:
        raise EdgeNotFoundError(edge_id)
    return edge


async def list_edges(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    source_node_id: Optional[uuid.UUID] = None,
    target_node_id: Optional[uuid.UUID] = None,
    edge_type: Optional[str] = None,
    active_only: bool = True,
    limit: int = 100,
) -> Sequence[GraphEdge]:
    now = datetime.now(timezone.utc)
    q = (
        select(GraphEdge)
        .where(and_(GraphEdge.project_id == project_id, GraphEdge.tenant_id == tenant_id))
        .limit(limit)
    )
    if source_node_id is not None:
        q = q.where(GraphEdge.source_node_id == source_node_id)
    if target_node_id is not None:
        q = q.where(GraphEdge.target_node_id == target_node_id)
    if edge_type is not None:
        q = q.where(GraphEdge.edge_type == edge_type)
    if active_only:
        from sqlalchemy import or_
        q = q.where(or_(GraphEdge.expires_at.is_(None), GraphEdge.expires_at > now))
    result = await session.execute(q)
    return result.scalars().all()


async def expire_edge(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    edge_id: uuid.UUID,
) -> GraphEdge:
    edge = await get_edge(session, tenant_id, edge_id)
    edge.expires_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(edge)
    return edge
