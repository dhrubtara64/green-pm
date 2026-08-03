"""Evidence Engine Pydantic schemas — S3-01."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_CAPTURE_TYPES = frozenset({
    "site_photo", "site_video", "voice_memo", "document_upload",
    "qr_scan", "form_submission", "iot_sensor", "drone_image",
    "surveyor_report", "inspection_report", "weather_log", "financial_document",
})

_EVIDENCE_STATUSES = frozenset({
    "draft", "submitted", "under_review", "approved", "rejected", "archived",
})

_RELIABILITY_TIERS = frozenset({"primary", "secondary", "tertiary"})

# Capture types that trigger async AI processing
_VISION_CAPTURE_TYPES = frozenset({"site_photo", "drone_image"})
_SPEECH_CAPTURE_TYPES = frozenset({"voice_memo"})
_OCR_CAPTURE_TYPES = frozenset({
    "document_upload", "surveyor_report", "inspection_report", "financial_document",
})

# Default reliability tier per capture type
_DEFAULT_RELIABILITY: dict[str, str] = {
    "site_photo": "secondary",
    "site_video": "secondary",
    "voice_memo": "secondary",
    "document_upload": "secondary",
    "qr_scan": "secondary",
    "form_submission": "secondary",
    "iot_sensor": "primary",
    "drone_image": "secondary",
    "surveyor_report": "primary",
    "inspection_report": "primary",
    "weather_log": "secondary",
    "financial_document": "primary",
}


class EvidenceCreate(BaseModel):
    project_id: uuid.UUID
    entity_type: str = Field(..., min_length=1, max_length=64)
    entity_id: uuid.UUID
    capture_type: str
    description: Optional[str] = Field(None, max_length=2000)
    file_ref: Optional[str] = None
    gcp_bucket: Optional[str] = None
    gcp_object: Optional[str] = None
    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    reliability_tier: Optional[str] = None
    captured_at: Optional[datetime] = None
    metadata: dict[str, Any] = {}

    @field_validator("capture_type")
    @classmethod
    def validate_capture_type(cls, v: str) -> str:
        if v not in _CAPTURE_TYPES:
            raise ValueError(
                f"Invalid capture_type {v!r}. Must be one of: {sorted(_CAPTURE_TYPES)}"
            )
        return v

    @field_validator("reliability_tier")
    @classmethod
    def validate_reliability_tier(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _RELIABILITY_TIERS:
            raise ValueError(
                f"Invalid reliability_tier {v!r}. Must be one of: {sorted(_RELIABILITY_TIERS)}"
            )
        return v

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def apply_defaults(self) -> "EvidenceCreate":
        if self.reliability_tier is None and self.capture_type in _DEFAULT_RELIABILITY:
            self.reliability_tier = _DEFAULT_RELIABILITY[self.capture_type]
        if self.captured_at is None:
            self.captured_at = datetime.now(timezone.utc)
        elif self.captured_at.tzinfo is None:
            self.captured_at = self.captured_at.replace(tzinfo=timezone.utc)
        return self

    @property
    def requires_vision(self) -> bool:
        return self.capture_type in _VISION_CAPTURE_TYPES

    @property
    def requires_speech(self) -> bool:
        return self.capture_type in _SPEECH_CAPTURE_TYPES

    @property
    def requires_ocr(self) -> bool:
        return self.capture_type in _OCR_CAPTURE_TYPES


class EvidenceUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)
    reliability_tier: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _EVIDENCE_STATUSES:
            raise ValueError(f"Invalid status {v!r}. Must be one of: {sorted(_EVIDENCE_STATUSES)}")
        return v

    @field_validator("reliability_tier")
    @classmethod
    def validate_reliability_tier(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _RELIABILITY_TIERS:
            raise ValueError(f"Invalid reliability_tier {v!r}")
        return v


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    capture_type: str
    status: str
    captured_by: Optional[uuid.UUID]
    captured_at: datetime
    file_ref: Optional[str]
    description: Optional[str]
    gcp_bucket: Optional[str]
    gcp_object: Optional[str]
    reliability_tier: str
    # ORM attr is evidence_metadata (SQLAlchemy reserves 'metadata'); alias maps both
    metadata: dict[str, Any] = Field(validation_alias="evidence_metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class EvidenceScoreResponse(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    score_value: float
    source_count: int
    recency_decay: float
    corroboration_ratio: float
    capture_diversity: float
    reliability_weight_avg: float
    computed_at: datetime

    model_config = {"from_attributes": True}
