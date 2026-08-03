"""PIG edge writer for evidence — S4-03.

On evidence approval, writes VERIFIES and REFERENCES edges to graph_edges
linking the evidence node to the target entity node.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.graph import GraphEdge, GraphNode
from shared.pig.sync import sync_entity

from ..evidence.model import Evidence


def _build_evidence_attributes(evidence: Evidence) -> dict:
    return {
        "capture_type": evidence.capture_type,
        "status": evidence.status,
        "entity_type": evidence.entity_type,
        "reliability_tier": evidence.reliability_tier,
    }


async def sync_evidence_node(
    session: AsyncSession,
    evidence: Evidence,
) -> GraphNode:
    """Register or update the PIG node for this evidence record."""
    return await sync_entity(
        session,
        tenant_id=evidence.tenant_id,
        project_id=evidence.project_id,
        entity_type="evidence",
        entity_id=evidence.id,
        attributes=_build_evidence_attributes(evidence),
    )


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


async def write_evidence_pig_edges(
    session: AsyncSession,
    evidence: Evidence,
    score_value: float,
) -> list[GraphEdge]:
    """Write VERIFIES + REFERENCES edges from evidence node → target entity node.

    Returns the list of created GraphEdge objects (may be empty if either node
    does not exist yet in the PIG — caller should ensure sync_evidence_node was
    called first).
    """
    source_node = await _find_node(
        session, evidence.tenant_id, evidence.project_id, "evidence", evidence.id
    )
    target_node = await _find_node(
        session, evidence.tenant_id, evidence.project_id, evidence.entity_type, evidence.entity_id
    )
    if source_node is None or target_node is None:
        return []

    created: list[GraphEdge] = []
    # VERIFIES carries the evidence score as weight; REFERENCES is a lighter structural link
    for edge_type, weight in [("VERIFIES", score_value), ("REFERENCES", 1.0)]:
        edge = GraphEdge(
            id=uuid.uuid4(),
            project_id=evidence.project_id,
            tenant_id=evidence.tenant_id,
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            edge_type=edge_type,
            weight=weight,
            metadata_={},
        )
        session.add(edge)
        created.append(edge)

    await session.flush()
    return created
