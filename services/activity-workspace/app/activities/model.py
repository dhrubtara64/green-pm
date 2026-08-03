"""Activity domain model — local to activity-workspace service.

Phase 0 has a single shared PostgreSQL instance; in later phases each
workspace service would own its own schema. For now the model lives here
and maps to the `activities` table that will be created in Sprint 2's
migration extension.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class Activity(Base, TenantIsolationMixin):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    wbs_code: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started")
    progress_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    planned_start: Mapped[Optional[date]] = mapped_column(Date)
    planned_finish: Mapped[Optional[date]] = mapped_column(Date)
    pig_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
