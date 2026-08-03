"""Unit tests for Activity Workspace schemas — S2-WS-01."""
import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.activities.schemas import ActivityCreate, ActivityResponse, ActivityUpdate


# ──────────────────────────────────────────────────────────────────────────────
# ActivityCreate
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityCreate:
    def _make(self, **kwargs):
        defaults = {
            "project_id": uuid.uuid4(),
            "name": "Excavation Works",
        }
        defaults.update(kwargs)
        return ActivityCreate(**defaults)

    def test_minimal_fields(self):
        a = self._make()
        assert a.name == "Excavation Works"
        assert a.status == "not_started"
        assert a.progress_pct == 0.0
        assert a.wbs_code is None
        assert a.planned_start is None
        assert a.planned_finish is None

    def test_all_fields(self):
        a = self._make(
            wbs_code="1.2.3",
            status="in_progress",
            progress_pct=42.5,
            planned_start=date(2026, 1, 1),
            planned_finish=date(2026, 3, 31),
        )
        assert a.wbs_code == "1.2.3"
        assert a.progress_pct == 42.5

    def test_name_stripped(self):
        a = self._make(name="  Pile Foundation  ")
        assert a.name == "Pile Foundation"

    def test_name_blank_raises(self):
        with pytest.raises(ValidationError, match="name must not be blank"):
            self._make(name="   ")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            self._make(name="x" * 256)

    def test_name_empty_string(self):
        with pytest.raises(ValidationError):
            self._make(name="")

    def test_valid_statuses(self):
        for s in ("not_started", "in_progress", "completed", "on_hold", "cancelled"):
            a = self._make(status=s)
            assert a.status == s

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            self._make(status="blocked")

    def test_progress_pct_zero(self):
        a = self._make(progress_pct=0.0)
        assert a.progress_pct == 0.0

    def test_progress_pct_100(self):
        a = self._make(progress_pct=100.0)
        assert a.progress_pct == 100.0

    def test_progress_pct_negative(self):
        with pytest.raises(ValidationError):
            self._make(progress_pct=-0.1)

    def test_progress_pct_over_100(self):
        with pytest.raises(ValidationError):
            self._make(progress_pct=100.1)

    def test_finish_before_start_raises(self):
        with pytest.raises(ValidationError, match="planned_finish must not be before planned_start"):
            self._make(
                planned_start=date(2026, 6, 1),
                planned_finish=date(2026, 5, 1),
            )

    def test_finish_equals_start_ok(self):
        a = self._make(
            planned_start=date(2026, 3, 1),
            planned_finish=date(2026, 3, 1),
        )
        assert a.planned_finish == a.planned_start

    def test_finish_after_start_ok(self):
        a = self._make(
            planned_start=date(2026, 1, 1),
            planned_finish=date(2026, 12, 31),
        )
        assert a.planned_finish > a.planned_start

    def test_only_start_no_finish(self):
        a = self._make(planned_start=date(2026, 1, 1))
        assert a.planned_finish is None

    def test_only_finish_no_start(self):
        a = self._make(planned_finish=date(2026, 12, 31))
        assert a.planned_start is None

    def test_wbs_code_max_length(self):
        a = self._make(wbs_code="1" * 50)
        assert len(a.wbs_code) == 50

    def test_wbs_code_too_long(self):
        with pytest.raises(ValidationError):
            self._make(wbs_code="1" * 51)

    def test_project_id_required(self):
        with pytest.raises(ValidationError):
            ActivityCreate(name="Test")

    def test_project_id_must_be_uuid(self):
        with pytest.raises(ValidationError):
            self._make(project_id="not-a-uuid")


# ──────────────────────────────────────────────────────────────────────────────
# ActivityUpdate
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityUpdate:
    def test_empty_update_ok(self):
        u = ActivityUpdate()
        assert u.model_dump(exclude_unset=True) == {}

    def test_name_only(self):
        u = ActivityUpdate(name="Revised Name")
        d = u.model_dump(exclude_unset=True)
        assert d == {"name": "Revised Name"}

    def test_name_stripped(self):
        u = ActivityUpdate(name="  Trimmed  ")
        assert u.name == "Trimmed"

    def test_name_blank_raises(self):
        with pytest.raises(ValidationError, match="name must not be blank"):
            ActivityUpdate(name="   ")

    def test_status_only(self):
        u = ActivityUpdate(status="completed")
        assert u.status == "completed"

    def test_progress_pct_only(self):
        u = ActivityUpdate(progress_pct=75.0)
        assert u.progress_pct == 75.0

    def test_progress_pct_negative(self):
        with pytest.raises(ValidationError):
            ActivityUpdate(progress_pct=-1.0)

    def test_progress_pct_over_100(self):
        with pytest.raises(ValidationError):
            ActivityUpdate(progress_pct=100.01)

    def test_dates_optional(self):
        u = ActivityUpdate(planned_start=date(2026, 2, 1))
        d = u.model_dump(exclude_unset=True)
        assert "planned_start" in d

    def test_partial_update_only_changed_fields(self):
        u = ActivityUpdate(status="on_hold", progress_pct=10.0)
        d = u.model_dump(exclude_unset=True)
        assert set(d.keys()) == {"status", "progress_pct"}


# ──────────────────────────────────────────────────────────────────────────────
# ActivityResponse
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityResponse:
    def _base(self):
        return {
            "id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
            "tenant_id": uuid.uuid4(),
            "name": "Concrete Pour",
            "wbs_code": None,
            "status": "in_progress",
            "progress_pct": 35.0,
            "planned_start": None,
            "planned_finish": None,
            "pig_node_id": None,
        }

    def test_from_dict(self):
        r = ActivityResponse(**self._base())
        assert r.name == "Concrete Pour"
        assert r.pig_node_id is None

    def test_with_pig_node_id(self):
        data = self._base()
        data["pig_node_id"] = uuid.uuid4()
        r = ActivityResponse(**data)
        assert r.pig_node_id is not None

    def test_from_attributes_config(self):
        assert ActivityResponse.model_config.get("from_attributes") is True
