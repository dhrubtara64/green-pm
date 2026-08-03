"""ORM models for the Readiness Engine — S10-01."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class ReadinessGate(Base, TenantIsolationMixin):
    """A named readiness gate (one of six types) for a project."""

    __tablename__ = "readiness_gates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # ENGINEERING | MATERIAL | CONSTRUCTION | QUALITY | COMMISSIONING | COD
    gate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_STARTED")
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ReadinessCriterion(Base, TenantIsolationMixin):
    """A single checklist item within a readiness gate."""

    __tablename__ = "readiness_criteria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    gate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    gate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    # PENDING | MET | WAIVED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    responsible_party: Mapped[Optional[str]] = mapped_column(String(200))
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ReadinessScore(Base, TenantIsolationMixin):
    """Snapshot of a gate's computed readiness metrics at a point in time."""

    __tablename__ = "readiness_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    gate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    gate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    total_criteria: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    met_criteria: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waived_criteria: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
