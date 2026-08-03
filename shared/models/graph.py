from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TenantIsolationMixin

GRAPH_NODE_ENTITY_TYPES = [
    "activity", "milestone", "drawing", "document", "equipment",
    "vendor", "dispatch", "evidence", "change", "decision",
    "risk", "issue", "gate", "wbs", "package", "shipment",
    "claim", "payment", "inspection", "commissioning_item",
    "organizational_unit", "person",
]

GRAPH_EDGE_TYPES = [
    "BLOCKS", "SUPPLIES_TO", "APPROVED_BY", "IMPACTS", "DEPENDS_ON",
    "SUPERSEDES", "CONFLICTS_WITH", "DELIVERS_FOR", "REVIEWS", "ASSIGNED_TO",
    "COORDINATES_WITH", "ESCALATES_TO", "PRECEDED_BY", "PARALLEL_WITH",
    "REQUIRES", "SATISFIES", "VERIFIES", "CLOSES", "MONITORS", "TRIGGERS",
    "OWNS", "RAISED_BY", "RESOLVED_BY", "REFERENCES", "SUPERSEDED_BY",
    "MITIGATES", "RAISES_RISK_TO", "CLEARS", "GATES", "REPORTS_TO",
]


class GraphEdgeType(Base):
    __tablename__ = "graph_edge_types"

    edge_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_directed: Mapped[bool] = mapped_column(nullable=False, default=True)


class GraphNode(Base, TenantIsolationMixin):
    __tablename__ = "graph_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class GraphEdge(Base, TenantIsolationMixin):
    __tablename__ = "graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(
        String(50), ForeignKey("graph_edge_types.edge_type"), nullable=False
    )
    weight: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=1.0)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
