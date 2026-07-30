"""
First-class join tables for all entity relationships.
Designed to migrate cleanly to a graph database in V2 — every relationship
is an explicit record with a typed relation_type, not an implicit FK or JSON blob.
"""
from sqlalchemy import Column, String, ForeignKey, Table
from app.database import Base


activity_evidence_items = Table(
    "activity_evidence_items",
    Base.metadata,
    Column("activity_id", String, ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_item_id", String, ForeignKey("evidence_items.id", ondelete="CASCADE"), primary_key=True),
    Column("relation_type", String, nullable=False, default="supports_progress_of"),
    # relation_type values: "supports_progress_of" | "contradicts"
)

activity_milestones = Table(
    "activity_milestones",
    Base.metadata,
    Column("activity_id", String, ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("milestone_id", String, ForeignKey("milestones.id", ondelete="CASCADE"), primary_key=True),
    # relation_type is always "rolls_up_to" for this relationship
)

deliverable_evidence_items = Table(
    "deliverable_evidence_items",
    Base.metadata,
    Column("deliverable_id", String, ForeignKey("deliverables.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_item_id", String, ForeignKey("evidence_items.id", ondelete="CASCADE"), primary_key=True),
    Column("relation_type", String, nullable=False, default="supports_progress_of"),
)
