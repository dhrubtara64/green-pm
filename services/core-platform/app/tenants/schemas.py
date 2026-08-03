from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


_VALID_PLANS = frozenset({"pilot", "professional", "enterprise"})


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    plan: Literal["pilot", "professional", "enterprise"] = "pilot"
    domain: Optional[str] = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @field_validator("domain")
    @classmethod
    def domain_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan: Optional[Literal["pilot", "professional", "enterprise"]] = None
    domain: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("name must not be blank")
        return v.strip() if v else v


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: str
    domain: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}
