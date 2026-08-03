from __future__ import annotations

import uuid
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_VALID_STATUSES = frozenset({
    "not_started", "in_progress", "completed", "on_hold", "cancelled"
})


class ActivityCreate(BaseModel):
    project_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    wbs_code: Optional[str] = Field(None, max_length=50)
    status: Literal["not_started", "in_progress", "completed", "on_hold", "cancelled"] = "not_started"
    progress_pct: float = Field(0.0, ge=0.0, le=100.0)
    planned_start: Optional[date] = None
    planned_finish: Optional[date] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @model_validator(mode="after")
    def finish_not_before_start(self) -> "ActivityCreate":
        if self.planned_start and self.planned_finish:
            if self.planned_finish < self.planned_start:
                raise ValueError("planned_finish must not be before planned_start")
        return self


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[Literal["not_started", "in_progress", "completed", "on_hold", "cancelled"]] = None
    progress_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    planned_start: Optional[date] = None
    planned_finish: Optional[date] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("name must not be blank")
        return v.strip() if v else v


class ActivityResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    wbs_code: Optional[str]
    status: str
    progress_pct: float
    planned_start: Optional[date]
    planned_finish: Optional[date]
    pig_node_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}
