"""ORM model for Recommendation Engine — S16-01."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class Recommendation(Base, TenantIsolationMixin):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_name: Mapped[str] = mapped_column(String(60), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(40), nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    projected_outcome: Mapped[Optional[str]] = mapped_column(Text)
    responsible_party: Mapped[Optional[str]] = mapped_column(String(200))
    evidence_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
