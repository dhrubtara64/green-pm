"""ORM models for the Risk Engine — S9-01."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class Risk(Base, TenantIsolationMixin):
    """Project risk with probability, impact, and lifecycle status."""

    __tablename__ = "risks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    impact: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RiskAssessment(Base, TenantIsolationMixin):
    """Monte Carlo assessment snapshot for a risk."""

    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    risk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_base: Mapped[float] = mapped_column(Float, nullable=False)
    schedule_std_dev: Mapped[float] = mapped_column(Float, nullable=False)
    cost_base: Mapped[float] = mapped_column(Float, nullable=False)
    cost_std_dev: Mapped[float] = mapped_column(Float, nullable=False)
    # Serialised MonteCarloResult: {iterations, schedule:{p10,p50,p80}, cost:{p10,p50,p80}}
    monte_carlo_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RiskMitigation(Base, TenantIsolationMixin):
    """Mitigation action tracked against a risk."""

    __tablename__ = "risk_mitigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    risk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    # Updated on outcome verification; 0.0 until verified
    effectiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    outcome_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class MemoryPattern(Base, TenantIsolationMixin):
    """Organisational memory pattern — stub table, expanded in Sprint 13."""

    __tablename__ = "memory_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    pattern_name: Mapped[str] = mapped_column(String(300), nullable=False)
    # JSONB list of keyword strings used for matching
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    historical_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_base: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
