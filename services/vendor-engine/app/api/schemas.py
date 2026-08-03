"""API request/response schemas for /vendors, /vendors/{id}/score, /vendors/{id}/rfis — S8-05."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Vendor ────────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    project_id: uuid.UUID
    vendor_code: Optional[str] = None
    contact_email: Optional[str] = None

class VendorResponse(BaseModel):
    id: uuid.UUID
    name: str
    project_id: uuid.UUID
    vendor_code: Optional[str] = None
    contact_email: Optional[str] = None
    status: str = "active"
    model_config = {"from_attributes": True}


# ── Vendor Score ──────────────────────────────────────────────────────────────

class VendorScoreRequest(BaseModel):
    """Dimensions must each be in [0, 100]."""
    quality: float = Field(ge=0.0, le=100.0)
    delivery: float = Field(ge=0.0, le=100.0)
    responsiveness: float = Field(ge=0.0, le=100.0)
    documentation: float = Field(ge=0.0, le=100.0)
    commercial: float = Field(ge=0.0, le=100.0)
    relationship: float = Field(ge=0.0, le=100.0)
    weights: Optional[dict[str, float]] = None

class VendorScoreResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    overall_score: float
    dimension_scores: dict[str, float]
    weights: dict[str, float]
    computed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class VendorScoreHistoryResponse(BaseModel):
    vendor_id: uuid.UUID
    history: list[VendorScoreResponse]


# ── RFI ───────────────────────────────────────────────────────────────────────

class RFIStatusFilter(str, Enum):
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    CLOSED = "CLOSED"
    ALL = "ALL"

class RFICreate(BaseModel):
    rfi_number: str
    title: str
    description: Optional[str] = None

class RFIResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    project_id: uuid.UUID
    rfi_number: str
    title: str
    description: Optional[str] = None
    status: str
    raised_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
