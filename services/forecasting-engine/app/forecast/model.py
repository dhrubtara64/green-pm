"""ORM models for the Forecasting Engine — S14-01."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class ForecastRecord(Base, TenantIsolationMixin):
    """One forecast snapshot per domain per project."""

    __tablename__ = "forecast_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    domain: Mapped[str] = mapped_column(String(30), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    trend: Mapped[str] = mapped_column(String(10), nullable=False, default="STABLE")
    computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
