"""ORM models for the Simulation Engine — S11-01."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class Scenario(Base, TenantIsolationMixin):
    """A named what-if scenario capturing a PIG snapshot and perturbation set."""

    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    baseline_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB)
    # DRAFT | ACTIVE | ARCHIVED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ScenarioPerturbation(Base, TenantIsolationMixin):
    """A single field-level perturbation applied to a PIG node within a scenario."""

    __tablename__ = "scenario_perturbations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    original_value: Mapped[float] = mapped_column(Float, nullable=False)
    perturbed_value: Mapped[float] = mapped_column(Float, nullable=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ScenarioProjection(Base, TenantIsolationMixin):
    """Computed forward projection for a scenario — schedule delta, budget delta, critical path."""

    __tablename__ = "scenario_projections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    schedule_delta_days: Mapped[float] = mapped_column(Float, nullable=False)
    budget_delta_pct: Mapped[float] = mapped_column(Float, nullable=False)
    critical_path_changes: Mapped[Optional[dict]] = mapped_column(JSONB)
    projected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
