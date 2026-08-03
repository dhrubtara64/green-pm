"""Evidence Review schemas — S4-01."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_REVIEW_OUTCOMES = frozenset({"approved", "rejected", "needs_revision"})


class EvidenceReviewCreate(BaseModel):
    outcome: str
    comments: Optional[str] = Field(None, max_length=4000)
    reliability_weight: float = Field(1.0, ge=0.0, le=1.0)

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        if v not in _REVIEW_OUTCOMES:
            raise ValueError(
                f"Invalid outcome {v!r}. Must be one of: {sorted(_REVIEW_OUTCOMES)}"
            )
        return v


class EvidenceReviewResponse(BaseModel):
    id: uuid.UUID
    evidence_id: uuid.UUID
    reviewer_id: uuid.UUID
    outcome: str
    comments: Optional[str]
    reviewed_at: datetime
    reliability_weight: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
