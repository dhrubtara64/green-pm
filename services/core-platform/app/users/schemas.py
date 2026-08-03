from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


_VALID_ROLES = frozenset({
    "super_admin", "tenant_admin", "project_manager",
    "engineer", "vendor_portal", "executive", "viewer",
})


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: Literal[
        "super_admin", "tenant_admin", "project_manager",
        "engineer", "vendor_portal", "executive", "viewer"
    ] = "engineer"
    google_sub: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[Literal[
        "super_admin", "tenant_admin", "project_manager",
        "engineer", "vendor_portal", "executive", "viewer"
    ]] = None
    is_active: Optional[bool] = None
    google_sub: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("name must not be blank")
        return v.strip() if v else v


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
