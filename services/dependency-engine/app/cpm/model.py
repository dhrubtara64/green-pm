"""ORM model for persisted CPM results."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class CriticalPathResult(Base, TenantIsolationMixin):
    __tablename__ = "critical_path_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    project_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    critical_path_activity_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    near_critical_activity_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    activity_floats: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="computed")
    computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
