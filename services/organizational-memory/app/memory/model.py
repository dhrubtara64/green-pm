"""Organizational Memory Engine ORM models — S13-01."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class MemoryRecord(Base, TenantIsolationMixin):
    __tablename__ = "memory_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    context: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    outcome: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class MemoryPattern(Base, TenantIsolationMixin):
    __tablename__ = "memory_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    pattern_name: Mapped[str] = mapped_column(String(300), nullable=False)
    trigger_conditions: Mapped[Optional[dict]] = mapped_column(JSONB)
    historical_outcomes: Mapped[Optional[list]] = mapped_column(JSONB)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class MemoryContribution(Base, TenantIsolationMixin):
    __tablename__ = "memory_contributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    memory_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    memory_pattern_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    contributed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
