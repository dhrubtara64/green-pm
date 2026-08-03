from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventEnvelope(BaseModel):
    """Immutable envelope for all Green PM domain events.

    Engineers must not publish events without this envelope.
    See Engineering Standards § 4: Event Design Rules.
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    schema_version: str = "1.0.0"
    tenant_id: UUID
    project_id: Optional[UUID] = None
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: Optional[UUID] = None
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @field_validator("schema_version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(
                f"schema_version must be SemVer (e.g. 1.0.0), got: {v!r}"
            )
        return v

    @field_validator("event_type")
    @classmethod
    def validate_pascal_case(cls, v: str) -> str:
        if not v or not v[0].isupper():
            raise ValueError(
                f"event_type must be PascalCase (e.g. ActivityDelayed), got: {v!r}"
            )
        if "_" in v or not any(c.islower() for c in v):
            raise ValueError(
                f"event_type must be PascalCase (no underscores, mixed case), got: {v!r}"
            )
        return v
