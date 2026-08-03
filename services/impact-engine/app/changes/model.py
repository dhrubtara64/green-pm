"""Change and ImpactAssessment ORM models — Impact Analysis Engine."""
from __future__ import annotations

import uuid
from typing import Optional

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class Change(Base, TenantIsolationMixin):
    __tablename__ = "changes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="initiated")
    change_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))


class ImpactAssessment(Base, TenantIsolationMixin):
    __tablename__ = "impact_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    change_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("changes.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    affected_entity_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    impact_graph_edges: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    narrative_summary: Mapped[Optional[str]] = mapped_column(Text)
    computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
