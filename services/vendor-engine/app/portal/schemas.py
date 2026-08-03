"""Read-only vendor portal API schemas — S8-04."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VendorPortalScoreResponse(BaseModel):
    """Vendor-scoped score response for the external portal."""
    vendor_id: uuid.UUID
    overall_score: float
    dimension_scores: dict[str, float]
    computed_at: Optional[datetime] = None
    trend_direction: str   # IMPROVING | STABLE | DECLINING
    predicted_score_30d: float
    model_config = {"from_attributes": True}


class VendorPortalRFIResponse(BaseModel):
    """Vendor-scoped RFI summary for the external portal."""
    id: uuid.UUID
    rfi_number: str
    title: str
    status: str           # OPEN | RESPONDED | CLOSED
    raised_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class VendorPortalSummaryResponse(BaseModel):
    """Top-level portal summary — combines score + open RFI count."""
    vendor_id: uuid.UUID
    overall_score: float
    trend_direction: str
    open_rfi_count: int
    last_scored_at: Optional[datetime] = None
