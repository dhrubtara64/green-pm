from sqlalchemy import Column, String, Float, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.associations import activity_evidence_items, activity_milestones


class Activity(Base):
    __tablename__ = "activities"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    wbs_ref = Column(String, nullable=True)
    discipline = Column(String, nullable=True)
    subcontractor = Column(String, nullable=True)
    source_schedule_ref = Column(String, nullable=True)

    reported_progress = Column(Float, nullable=False, default=0.0)

    # Two distinct scores — never merged, as required by Product Bible Section 10.6
    evidence_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)

    # AI reasoning for the confidence score (human-readable, citable)
    confidence_reasoning = Column(Text, nullable=True)

    # Specific named gap — never a generic flag
    missing_evidence = Column(Text, nullable=True)

    # Set when evidence_score < 0.25 AND confidence_score < 0.30,
    # OR when a contradicting EvidenceItem exists with no human resolution
    verification_required = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    evidence_items = relationship(
        "EvidenceItem",
        secondary=activity_evidence_items,
        back_populates="activities",
        lazy="selectin",
    )
    milestones = relationship(
        "Milestone",
        secondary=activity_milestones,
        back_populates="activities",
        lazy="selectin",
    )
    corrections = relationship(
        "HumanCorrection",
        back_populates="activity",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
