"""Unit tests for Change schemas — S5-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.changes.schemas import (
    ChangeCreate,
    ChangeResponse,
    ImpactAssessmentResponse,
    _CHANGE_TYPES,
)

_PROJ = uuid.uuid4()
_ENTITY = uuid.uuid4()


def _make(**kwargs) -> ChangeCreate:
    defaults = {
        "project_id": _PROJ,
        "entity_type": "activity",
        "entity_id": _ENTITY,
        "change_type": "scope_change",
    }
    defaults.update(kwargs)
    return ChangeCreate(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# ChangeCreate — change_type validation
# ──────────────────────────────────────────────────────────────────────────────

class TestChangeTypeValidation:
    @pytest.mark.parametrize("ct", sorted(_CHANGE_TYPES))
    def test_all_8_change_types_accepted(self, ct: str):
        c = _make(change_type=ct)
        assert c.change_type == ct

    def test_invalid_change_type_raises(self):
        with pytest.raises(ValidationError, match="Invalid change_type"):
            _make(change_type="budget_overrun")

    def test_change_type_case_sensitive(self):
        with pytest.raises(ValidationError):
            _make(change_type="Scope_Change")

    def test_8_distinct_change_types(self):
        assert len(_CHANGE_TYPES) == 8


# ──────────────────────────────────────────────────────────────────────────────
# ChangeCreate — required fields
# ──────────────────────────────────────────────────────────────────────────────

class TestChangeCreateRequiredFields:
    def test_project_id_required(self):
        with pytest.raises(ValidationError):
            ChangeCreate(entity_type="activity", entity_id=_ENTITY, change_type="scope_change")

    def test_entity_id_required(self):
        with pytest.raises(ValidationError):
            ChangeCreate(project_id=_PROJ, entity_type="activity", change_type="scope_change")

    def test_change_type_required(self):
        with pytest.raises(ValidationError):
            ChangeCreate(project_id=_PROJ, entity_type="activity", entity_id=_ENTITY)


# ──────────────────────────────────────────────────────────────────────────────
# ChangeCreate — optional fields
# ──────────────────────────────────────────────────────────────────────────────

class TestChangeCreateOptionalFields:
    def test_description_max_4000(self):
        c = _make(description="x" * 4000)
        assert len(c.description) == 4000

    def test_description_too_long_raises(self):
        with pytest.raises(ValidationError):
            _make(description="x" * 4001)

    def test_description_can_be_none(self):
        c = _make(description=None)
        assert c.description is None

    def test_metadata_defaults_to_empty_dict(self):
        c = _make()
        assert c.metadata == {}

    def test_metadata_accepts_arbitrary_dict(self):
        c = _make(metadata={"key": "value", "count": 3})
        assert c.metadata["key"] == "value"


# ──────────────────────────────────────────────────────────────────────────────
# ChangeResponse
# ──────────────────────────────────────────────────────────────────────────────

class TestChangeResponse:
    def _base_dict(self):
        now = datetime.now(timezone.utc)
        return {
            "id": uuid.uuid4(),
            "project_id": _PROJ,
            "tenant_id": uuid.uuid4(),
            "entity_type": "activity",
            "entity_id": _ENTITY,
            "change_type": "scope_change",
            "status": "initiated",
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }

    def test_from_dict(self):
        r = ChangeResponse(**self._base_dict())
        assert r.change_type == "scope_change"

    def test_from_attributes_config(self):
        assert ChangeResponse.model_config.get("from_attributes") is True

    def test_metadata_via_change_metadata_alias(self):
        mock_orm = MagicMock()
        mock_orm.description = None
        mock_orm.created_by = None
        for k, v in self._base_dict().items():
            if k == "metadata":
                setattr(mock_orm, "change_metadata", v)
            else:
                setattr(mock_orm, k, v)
        r = ChangeResponse.model_validate(mock_orm)
        assert r.metadata == {}

    def test_populate_by_name_allows_metadata_key(self):
        r = ChangeResponse(**self._base_dict())
        assert r.metadata == {}


# ──────────────────────────────────────────────────────────────────────────────
# ImpactAssessmentResponse
# ──────────────────────────────────────────────────────────────────────────────

class TestImpactAssessmentResponse:
    def test_from_attributes_config(self):
        assert ImpactAssessmentResponse.model_config.get("from_attributes") is True

    def test_all_required_fields(self):
        now = datetime.now(timezone.utc)
        r = ImpactAssessmentResponse(
            id=uuid.uuid4(),
            change_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            status="assessed",
            dimensions={"scope": {"value": 3.0, "unit": "node_count", "confidence_score": 0.3}},
            affected_entity_ids=["abc", "def"],
            impact_graph_edges=[],
            narrative_summary="Test narrative",
            computed_at=now,
            created_at=now,
        )
        assert r.status == "assessed"
        assert len(r.affected_entity_ids) == 2
