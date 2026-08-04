"""ORM model for Reporting Engine — S17-01."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class Report(Base, TenantIsolationMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    narrative: Mapped[Optional[str]] = mapped_column(Text)
    structured_data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    evidence_chain_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
