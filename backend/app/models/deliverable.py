from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.associations import deliverable_evidence_items


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)   # drawing | document | equipment | approval
    status = Column(String, nullable=True)  # pending | in_progress | submitted | approved | rejected

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    evidence_items = relationship(
        "EvidenceItem",
        secondary=deliverable_evidence_items,
        back_populates="deliverables",
        lazy="selectin",
    )
