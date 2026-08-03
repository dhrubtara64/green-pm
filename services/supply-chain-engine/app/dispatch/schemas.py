"""Pydantic schemas and domain constants for the dispatch lifecycle."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# 10-stage dispatch lifecycle — sequential, no skipping
_DISPATCH_STAGES: list[str] = [
    "PO_RAISED",
    "VENDOR_CONFIRMED",
    "MANUFACTURING",
    "QC_INSPECTION",
    "READY_FOR_DISPATCH",
    "DISPATCHED",
    "IN_TRANSIT",
    "ARRIVED_AT_SITE",
    "INSPECTED_ON_SITE",
    "ACCEPTED",
]

# Maps each stage → its only valid successor (None for terminal)
_VALID_TRANSITIONS: dict[str, Optional[str]] = {
    stage: (_DISPATCH_STAGES[i + 1] if i + 1 < len(_DISPATCH_STAGES) else None)
    for i, stage in enumerate(_DISPATCH_STAGES)
}

_STAGE_INDEX: dict[str, int] = {s: i for i, s in enumerate(_DISPATCH_STAGES)}

_SUPPLY_CHAIN_TOPIC = "greenpm.supply"
_CRITICALITY_WEIGHT = 2.0  # critical items count this many times non-critical


# ── Vendor ────────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    project_id: uuid.UUID
    contact_email: Optional[str] = None
    vendor_code: Optional[str] = None

class VendorResponse(BaseModel):
    id: uuid.UUID
    name: str
    project_id: uuid.UUID
    contact_email: Optional[str] = None
    vendor_code: Optional[str] = None
    model_config = {"from_attributes": True}


# ── PurchaseOrder ─────────────────────────────────────────────────────────────

class PurchaseOrderCreate(BaseModel):
    vendor_id: uuid.UUID
    project_id: uuid.UUID
    po_number: str
    total_value: float = Field(ge=0.0)
    currency: str = "USD"
    expected_delivery: Optional[datetime] = None

class PurchaseOrderResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    project_id: uuid.UUID
    po_number: str
    total_value: float
    currency: str
    status: str
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Dispatch ──────────────────────────────────────────────────────────────────

class DispatchCreate(BaseModel):
    po_id: uuid.UUID
    project_id: uuid.UUID
    dispatch_number: str

class DispatchResponse(BaseModel):
    id: uuid.UUID
    po_id: uuid.UUID
    project_id: uuid.UUID
    dispatch_number: str
    current_stage: str
    material_readiness_score: float
    critical_material_count: int
    model_config = {"from_attributes": True}

class StageTransitionRequest(BaseModel):
    target_stage: str

class StageTransitionResponse(BaseModel):
    dispatch_id: uuid.UUID
    previous_stage: str
    current_stage: str
    material_readiness_score: float
    transitioned_at: datetime


# ── MaterialPackage ───────────────────────────────────────────────────────────

class MaterialPackageCreate(BaseModel):
    dispatch_id: uuid.UUID
    project_id: uuid.UUID
    package_number: str
    description: Optional[str] = None

class MaterialPackageResponse(BaseModel):
    id: uuid.UUID
    dispatch_id: uuid.UUID
    project_id: uuid.UUID
    package_number: str
    description: Optional[str] = None
    status: str
    model_config = {"from_attributes": True}


# ── MaterialItem ──────────────────────────────────────────────────────────────

class MaterialItemCreate(BaseModel):
    package_id: uuid.UUID
    project_id: uuid.UUID
    description: str
    quantity: float = Field(gt=0.0)
    unit: str
    activity_id: Optional[uuid.UUID] = None  # links to PIG activity for critical path check

class MaterialItemResponse(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    project_id: uuid.UUID
    description: str
    quantity: float
    unit: str
    is_critical: bool
    activity_id: Optional[uuid.UUID] = None
    model_config = {"from_attributes": True}
