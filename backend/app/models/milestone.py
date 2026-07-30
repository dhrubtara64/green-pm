from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.associations import activity_milestones


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    target_date = Column(Date, nullable=True)
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    activities = relationship(
        "Activity",
        secondary=activity_milestones,
        back_populates="milestones",
        lazy="selectin",
    )
