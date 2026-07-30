from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(String, primary_key=True)

    # The AI-drafted report content (fully editable by human before "send")
    draft_content = Column(Text, nullable=False)

    # Human-edited version (None until a human edits)
    edited_content = Column(Text, nullable=True)

    # Snapshot of activity statuses at report generation time
    activities_snapshot = Column(Text, nullable=True)  # JSON string

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # When a human confirmed this report (clicked "Send")
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # "Send" is always a logged no-op in V1 — records the intent, no real email
    send_log = Column(Text, nullable=True)
