"""User schema unit tests — S1-CORE-03."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.users.schemas import UserCreate, UserResponse, UserUpdate


def test_create_defaults():
    u = UserCreate(email="alice@example.com", name="Alice")
    assert u.role == "engineer"
    assert u.google_sub is None


def test_create_name_stripped():
    u = UserCreate(email="bob@example.com", name="  Bob  ")
    assert u.name == "Bob"


def test_create_invalid_email_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", name="X")


def test_create_blank_name_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", name="   ")


def test_create_invalid_role_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", name="X", role="hacker")  # type: ignore[arg-type]


@pytest.mark.parametrize("role", [
    "super_admin", "tenant_admin", "project_manager",
    "engineer", "vendor_portal", "executive", "viewer",
])
def test_create_all_valid_roles(role):
    u = UserCreate(email="a@b.com", name="X", role=role)  # type: ignore[arg-type]
    assert u.role == role


def test_update_all_optional():
    u = UserUpdate()
    assert u.name is None
    assert u.role is None
    assert u.is_active is None


def test_update_excludes_unset():
    u = UserUpdate(is_active=True)
    data = u.model_dump(exclude_unset=True)
    assert "is_active" in data
    assert "name" not in data


def test_response_from_attributes():
    class FakeUser:
        id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        email = "carol@example.com"
        name = "Carol"
        role = "engineer"
        is_active = True

    r = UserResponse.model_validate(FakeUser())
    assert r.email == "carol@example.com"
    assert r.is_active is True
