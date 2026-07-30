from datetime import datetime
from pydantic import BaseModel
from app.schemas.evidence_item import EvidenceItemOut


class ActivitySummary(BaseModel):
    """Lightweight view for the dashboard list."""
    id: str
    name: str
    wbs_ref: str | None
    discipline: str | None
    reported_progress: float
    evidence_score: float
    confidence_score: float
    missing_evidence: str | None
    verification_required: bool
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ActivityDetail(ActivitySummary):
    """Full view including evidence trail and AI reasoning."""
    confidence_reasoning: str | None
    evidence_items: list[EvidenceItemOut] = []

    model_config = {"from_attributes": True}


class ConfirmRequest(BaseModel):
    field_name: str
    current_value: str


class CorrectRequest(BaseModel):
    field_name: str
    old_value: str
    new_value: str
    rationale: str | None = None


class CorrectionOut(BaseModel):
    id: str
    activity_id: str
    field_name: str
    old_value: str | None
    new_value: str | None
    action: str
    corrected_at: datetime

    model_config = {"from_attributes": True}
