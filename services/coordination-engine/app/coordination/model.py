"""ORM models for the Coordination Engine — S12-01."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from shared.models.base import Base, TenantIsolationMixin


class CoordinationItem(Base, TenantIsolationMixin):
    __tablename__ = "coordination_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    stage_timestamps: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class CoordinationClosure(Base, TenantIsolationMixin):
    __tablename__ = "coordination_closures"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    coordination_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    closed_by: Mapped[Optional[str]] = mapped_column(String(200))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
