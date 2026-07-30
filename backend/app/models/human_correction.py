from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class HumanCorrection(Base):
    """
    Log of every human Confirm or Correct action on an AI inference.
    Feeds future calibration loop (loop not built in V1, but data captured here).
    """
    __tablename__ = "human_corrections"

    id = Column(String, primary_key=True)
    activity_id = Column(String, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String, nullable=False)   # e.g. "reported_progress", "confidence_score"
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    action = Column(String, nullable=False)       # "confirm" | "correct"
    corrected_at = Column(DateTime(timezone=True), server_default=func.now())

    # Human-provided rationale (optional, captured for calibration)
    rationale = Column(Text, nullable=True)

    activity = relationship("Activity", back_populates="corrections")
