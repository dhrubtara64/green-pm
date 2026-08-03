"""Unit tests for dependency graph API schemas — S6-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.dependencies.schemas import ActivityDependencyInfo, DependencyGraphResponse


_PROJECT = uuid.uuid4()
_ACTIVITY = uuid.uuid4()
_NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def _make_float_entry(total_float=0.0, is_critical=True) -> dict:
    return {
        "early_start": 0.0,
        "early_finish": 5.0,
        "late_start": 0.0,
        "late_finish": 5.0,
        "total_float": total_float,
        "free_float": 0.0,
        "is_critical": is_critical,
    }


# ──────────────────────────────────────────────────────────────────────────────
# ActivityDependencyInfo
# ──────────────────────────────────────────────────────────────────────────────

class TestActivityDependencyInfo:
    def _make(self, total_float=0.0, is_critical=True) -> ActivityDependencyInfo:
        return ActivityDependencyInfo(
            activity_id=_ACTIVITY,
            early_start=0.0,
            early_finish=5.0,
            late_start=0.0,
            late_finish=5.0,
            total_float=total_float,
            free_float=0.0,
            is_critical=is_critical,
            predecessors=[],
            successors=[],
        )

    def test_stores_activity_id(self):
        info = self._make()
        assert info.activity_id == _ACTIVITY

    def test_stores_is_critical(self):
        info = self._make(is_critical=False)
        assert info.is_critical is False

    def test_stores_total_float(self):
        info = self._make(total_float=2.5)
        assert info.total_float == pytest.approx(2.5)

    def test_stores_predecessors(self):
        pred_id = str(uuid.uuid4())
        info = ActivityDependencyInfo(
            activity_id=_ACTIVITY,
            early_start=0.0, early_finish=5.0,
            late_start=0.0, late_finish=5.0,
            total_float=0.0, free_float=0.0, is_critical=True,
            predecessors=[pred_id], successors=[],
        )
        assert pred_id in info.predecessors

    def test_stores_successors(self):
        succ_id = str(uuid.uuid4())
        info = ActivityDependencyInfo(
            activity_id=_ACTIVITY,
            early_start=0.0, early_finish=5.0,
            late_start=0.0, late_finish=5.0,
            total_float=0.0, free_float=0.0, is_critical=True,
            predecessors=[], successors=[succ_id],
        )
        assert succ_id in info.successors


# ──────────────────────────────────────────────────────────────────────────────
# DependencyGraphResponse
# ──────────────────────────────────────────────────────────────────────────────

class TestDependencyGraphResponse:
    def _make_response(self) -> DependencyGraphResponse:
        aid_str = str(_ACTIVITY)
        return DependencyGraphResponse.from_cpm_result(
            project_id=_PROJECT,
            computed_at=_NOW,
            project_duration=5.0,
            critical_path=[aid_str],
            near_critical=[],
            activity_floats={aid_str: _make_float_entry()},
            predecessors_map={},
            successors_map={},
        )

    def test_stores_project_id(self):
        r = self._make_response()
        assert r.project_id == _PROJECT

    def test_stores_project_duration(self):
        r = self._make_response()
        assert r.project_duration == pytest.approx(5.0)

    def test_critical_path_contains_str_uuid(self):
        r = self._make_response()
        assert str(_ACTIVITY) in r.critical_path

    def test_activities_list_populated(self):
        r = self._make_response()
        assert len(r.activities) == 1

    def test_activity_has_correct_id(self):
        r = self._make_response()
        assert r.activities[0].activity_id == _ACTIVITY

    def test_from_cpm_result_empty_floats_gives_empty_activities(self):
        r = DependencyGraphResponse.from_cpm_result(
            project_id=_PROJECT,
            computed_at=_NOW,
            project_duration=0.0,
            critical_path=[],
            near_critical=[],
            activity_floats={},
            predecessors_map={},
            successors_map={},
        )
        assert r.activities == []

    def test_near_critical_list_populated(self):
        aid_str = str(_ACTIVITY)
        r = DependencyGraphResponse.from_cpm_result(
            project_id=_PROJECT,
            computed_at=_NOW,
            project_duration=5.0,
            critical_path=[],
            near_critical=[aid_str],
            activity_floats={aid_str: _make_float_entry(total_float=1.5, is_critical=False)},
            predecessors_map={},
            successors_map={},
        )
        assert aid_str in r.near_critical
