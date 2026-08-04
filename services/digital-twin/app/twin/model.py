"""ORM models for Executive Digital Twin + Command Centre — S17-02, S17-03."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class EDTSynthesis(Base, TenantIsolationMixin):
    """One Monday synthesis snapshot — Reality + Forecast + Required Decisions."""

    __tablename__ = "edt_syntheses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    synthesis_date: Mapped[date] = mapped_column(Date, nullable=False)
    reality_panel: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    forecast_panel: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    decisions_panel: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    synthesized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class CommandCentrePanel(Base, TenantIsolationMixin):
    """One real-time panel in the Project Command Centre — updated on engine events."""

    __tablename__ = "command_centre_panels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    panel_name: Mapped[str] = mapped_column(String(30), nullable=False)
    panel_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    triggered_by_event: Mapped[Optional[str]] = mapped_column(String(100))
