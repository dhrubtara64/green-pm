"""Project schema unit tests — S1-CORE-02."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate


def test_create_code_uppercased():
    p = ProjectCreate(name="Omega Bridge", project_code="omg-001")
    assert p.project_code == "OMG-001"


def test_create_defaults():
    p = ProjectCreate(name="X", project_code="X001")
    assert p.status == "active"


def test_create_blank_name_rejected():
    with pytest.raises(ValidationError):
        ProjectCreate(name="  ", project_code="X001")


def test_create_blank_code_rejected():
    with pytest.raises(ValidationError):
        ProjectCreate(name="X", project_code="  ")


def test_create_invalid_status_rejected():
    with pytest.raises(ValidationError):
        ProjectCreate(name="X", project_code="X001", status="cancelled")  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["active", "archived", "on_hold"])
def test_create_all_valid_statuses(status):
    p = ProjectCreate(name="X", project_code="X001", status=status)  # type: ignore[arg-type]
    assert p.status == status


def test_update_all_optional():
    u = ProjectUpdate()
    assert u.name is None
    assert u.status is None


def test_update_excludes_unset():
    u = ProjectUpdate(status="archived")
    data = u.model_dump(exclude_unset=True)
    assert "status" in data
    assert "name" not in data


def test_response_from_attributes():
    class FakeProject:
        id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        name = "Bridge"
        project_code = "BRG-001"
        status = "active"

    r = ProjectResponse.model_validate(FakeProject())
    assert r.project_code == "BRG-001"
    assert r.status == "active"
