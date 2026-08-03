"""Evidence domain models — local to evidence-engine service."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin, TimestampMixin

_CAPTURE_TYPES = (
    "site_photo", "site_video", "voice_memo", "document_upload",
    "qr_scan", "form_submission", "iot_sensor", "drone_image",
    "surveyor_report", "inspection_report", "weather_log", "financial_document",
)
_EVIDENCE_STATUSES = ("draft", "submitted", "under_review", "approved", "rejected", "archived")
_RELIABILITY_TIERS = ("primary", "secondary", "tertiary")


class Evidence(Base, TenantIsolationMixin, TimestampMixin):
    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    capture_type: Mapped[str] = mapped_column(
        Enum(*_CAPTURE_TYPES, name="capture_type"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(*_EVIDENCE_STATUSES, name="evidence_status"),
        nullable=False, default="draft",
    )
    captured_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    captured_at: Mapped[datetime] = mapped_column(nullable=False)
    file_ref: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    location_lat: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    location_lng: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    gcp_bucket: Mapped[Optional[str]] = mapped_column(Text)
    gcp_object: Mapped[Optional[str]] = mapped_column(Text)
    reliability_tier: Mapped[str] = mapped_column(
        Enum(*_RELIABILITY_TIERS, name="reliability_tier"),
        nullable=False, default="secondary",
    )
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class EvidenceReview(Base, TenantIsolationMixin):
    __tablename__ = "evidence_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidences.id"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        Enum("approved", "rejected", "needs_revision", name="evidence_review_outcome"),
        nullable=False,
    )
    comments: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(nullable=False)
    reliability_weight: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("1.0")
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class EvidenceScore(Base, TenantIsolationMixin):
    """Aggregate Evidence Score v5 per (project, entity_type, entity_id)."""
    __tablename__ = "evidence_scores"
    __table_args__ = (
        UniqueConstraint("project_id", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    score_value: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    source_count: Mapped[int] = mapped_column(nullable=False, default=0)
    recency_decay: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    corroboration_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    capture_diversity: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    reliability_weight_avg: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(nullable=False)
