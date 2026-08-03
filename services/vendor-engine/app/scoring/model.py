"""ORM models for vendor scoring and RFIs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class VendorScoreRecord(Base, TenantIsolationMixin):
    """Persisted snapshot of a vendor's scoring computation."""
    __tablename__ = "vendor_score_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # JSONB: {quality, delivery, responsiveness, documentation, commercial, relationship}
    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    # JSONB: {dimension → weight}
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # JSONB list of CausalAttribution dicts for this snapshot
    causal_attributions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RFI(Base, TenantIsolationMixin):
    """Request for Information raised against a vendor."""
    __tablename__ = "rfis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rfi_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    raised_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
