"""Tenant schema unit tests — S1-CORE-01.

Tests input validation, defaults, and field constraints.
No database required.
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.tenants.schemas import TenantCreate, TenantResponse, TenantUpdate


# ── TenantCreate ──────────────────────────────────────────────────────────────

def test_create_defaults():
    t = TenantCreate(name="Acme Corp")
    assert t.plan == "pilot"
    assert t.domain is None


def test_create_name_stripped():
    t = TenantCreate(name="  Acme Corp  ")
    assert t.name == "Acme Corp"


def test_create_domain_lowercased_and_stripped():
    t = TenantCreate(name="X", domain="  ACME.COM  ")
    assert t.domain == "acme.com"


def test_create_blank_name_rejected():
    with pytest.raises(ValidationError, match="blank"):
        TenantCreate(name="   ")


def test_create_name_too_long_rejected():
    with pytest.raises(ValidationError):
        TenantCreate(name="x" * 101)


def test_create_invalid_plan_rejected():
    with pytest.raises(ValidationError):
        TenantCreate(name="X", plan="freemium")  # type: ignore[arg-type]


@pytest.mark.parametrize("plan", ["pilot", "professional", "enterprise"])
def test_create_all_valid_plans(plan):
    t = TenantCreate(name="X", plan=plan)  # type: ignore[arg-type]
    assert t.plan == plan


# ── TenantUpdate ──────────────────────────────────────────────────────────────

def test_update_all_fields_optional():
    u = TenantUpdate()
    assert u.name is None
    assert u.plan is None
    assert u.domain is None
    assert u.is_active is None


def test_update_blank_name_rejected():
    with pytest.raises(ValidationError, match="blank"):
        TenantUpdate(name="  ")


def test_update_partial_excludes_unset():
    u = TenantUpdate(plan="enterprise")
    data = u.model_dump(exclude_unset=True)
    assert "plan" in data
    assert "name" not in data
    assert "is_active" not in data


# ── TenantResponse ────────────────────────────────────────────────────────────

def test_response_from_attributes():
    class FakeTenant:
        id = uuid.uuid4()
        name = "Acme"
        plan = "pilot"
        domain = None
        is_active = True

    r = TenantResponse.model_validate(FakeTenant())
    assert r.name == "Acme"
    assert r.is_active is True
