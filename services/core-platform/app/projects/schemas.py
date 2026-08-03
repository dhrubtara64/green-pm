from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    project_code: str = Field(..., min_length=1, max_length=50)
    status: Literal["active", "archived", "on_hold"] = "active"

    @field_validator("name", "project_code")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    @field_validator("project_code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        return v.strip().upper()


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[Literal["active", "archived", "on_hold"]] = None

    @field_validator("name")
    @classmethod
    def not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("name must not be blank")
        return v.strip() if v else v


class ProjectResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    project_code: str
    status: str

    model_config = {"from_attributes": True}
