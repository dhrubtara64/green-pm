"""ORM models for AI Orchestration Engine — S16-02, S16-04."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TenantIsolationMixin


class AISession(Base, TenantIsolationMixin):
    __tablename__ = "ai_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_chain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engines_consulted: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False, default="QUERY")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class EvidenceChainRecord(Base, TenantIsolationMixin):
    __tablename__ = "evidence_chains"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pig_node_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    scores_used: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    engines_consulted: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
