from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base
from app.models.associations import activity_evidence_items, deliverable_evidence_items


class SourceReliabilitySignal(str, enum.Enum):
    high = "high"          # Official approved documents, certified records
    medium = "medium"      # Progress reports, internal trackers, vendor updates
    low = "low"            # Informal updates, stale data, unverified field notes
    unverified = "unverified"  # First time from this source, no track record yet


class RelationType(str, enum.Enum):
    supports_progress_of = "supports_progress_of"
    contradicts = "contradicts"


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(String, primary_key=True)

    # Where this evidence came from (e.g. "schedule_xer", "document_folder", "boq_upload")
    source_system = Column(String, nullable=False)

    # Which ingestion connector produced this item
    ingesting_connector = Column(String, nullable=False)

    # Link back to the original source (filename, doc ref, sheet row)
    provenance_ref = Column(String, nullable=True)

    # The extracted fact/content from the source
    extracted_content = Column(Text, nullable=False)

    # Snippet of the original source text for the "show your work" evidence trail
    source_excerpt = Column(Text, nullable=True)

    # Default relation type for this evidence item (can be overridden per join table row)
    relation_type = Column(
        Enum(RelationType),
        nullable=False,
        default=RelationType.supports_progress_of,
    )

    # Reliability signal at time of ingestion
    source_reliability_signal = Column(
        Enum(SourceReliabilitySignal),
        nullable=False,
        default=SourceReliabilitySignal.unverified,
    )

    # When this evidence was produced (from the source document, not ingestion time)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # When this item was ingested
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    activities = relationship(
        "Activity",
        secondary=activity_evidence_items,
        back_populates="evidence_items",
        lazy="selectin",
    )
    deliverables = relationship(
        "Deliverable",
        secondary=deliverable_evidence_items,
        back_populates="evidence_items",
        lazy="selectin",
    )
