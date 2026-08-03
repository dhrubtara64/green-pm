"""Tests for material readiness and critical material services — S7-03, S7-04."""
import uuid
from dataclasses import dataclass
from typing import Optional

import pytest

from app.dispatch.schemas import _DISPATCH_STAGES
from app.materials.schemas import CriticalMaterialInfo, MaterialReadinessResult
from app.materials.service import (
    build_readiness_result,
    compute_readiness_score,
    identify_critical_materials,
)


class TestComputeReadinessScore:
    def test_first_stage_score_is_zero(self):
        assert compute_readiness_score("PO_RAISED") == 0.0

    def test_terminal_stage_score_is_100(self):
        assert compute_readiness_score("ACCEPTED") == 100.0

    def test_second_stage_score_correct(self):
        # index 1 / 9 * 100 = 11.11
        score = compute_readiness_score("VENDOR_CONFIRMED")
        assert abs(score - 11.11) < 0.01

    def test_middle_stage_score_correct(self):
        # DISPATCHED is index 5 → 5/9 * 100 = 55.56
        score = compute_readiness_score("DISPATCHED")
        assert abs(score - 55.56) < 0.01

    def test_score_increases_monotonically(self):
        scores = [compute_readiness_score(s) for s in _DISPATCH_STAGES]
        for i in range(len(scores) - 1):
            assert scores[i] < scores[i + 1]

    def test_score_without_items_same_as_with_balanced_items(self):
        # With items all at same stage, weighting simplifies to base_progress
        s_no_items = compute_readiness_score("DISPATCHED")
        s_with_items = compute_readiness_score("DISPATCHED", critical_item_count=2, total_item_count=4)
        assert abs(s_no_items - s_with_items) < 0.01

    def test_score_with_only_critical_items(self):
        # 2 critical, 0 non-critical → effective formula still base_progress * 100
        score = compute_readiness_score("ACCEPTED", critical_item_count=5, total_item_count=5)
        assert score == 100.0

    def test_score_with_zero_total_items_equals_base(self):
        base = compute_readiness_score("MANUFACTURING")
        with_zero = compute_readiness_score("MANUFACTURING", critical_item_count=0, total_item_count=0)
        assert base == with_zero

    def test_score_returns_float(self):
        assert isinstance(compute_readiness_score("PO_RAISED"), float)

    def test_unknown_stage_defaults_to_zero(self):
        score = compute_readiness_score("NONEXISTENT")
        assert score == 0.0


class TestBuildReadinessResult:
    def test_returns_material_readiness_result(self):
        result = build_readiness_result("PO_RAISED")
        assert isinstance(result, MaterialReadinessResult)

    def test_stage_stored_correctly(self):
        result = build_readiness_result("DISPATCHED")
        assert result.stage == "DISPATCHED"

    def test_stage_index_stored_correctly(self):
        result = build_readiness_result("DISPATCHED")
        assert result.stage_index == 5

    def test_score_matches_compute_readiness_score(self):
        result = build_readiness_result("MANUFACTURING", critical_item_count=1, total_item_count=3)
        expected = compute_readiness_score("MANUFACTURING", 1, 3)
        assert result.score == expected

    def test_critical_item_count_stored(self):
        result = build_readiness_result("IN_TRANSIT", critical_item_count=3, total_item_count=5)
        assert result.critical_item_count == 3
        assert result.total_item_count == 5

    def test_immutable_frozen_dataclass(self):
        result = build_readiness_result("PO_RAISED")
        with pytest.raises((AttributeError, TypeError)):
            result.stage = "ACCEPTED"


class TestIdentifyCriticalMaterials:
    @dataclass
    class _FakeItem:
        id: uuid.UUID
        activity_id: Optional[uuid.UUID]
        description: str

    def test_empty_items_returns_empty(self):
        result = identify_critical_materials([], critical_activity_ids=set())
        assert result == []

    def test_item_on_critical_path_flagged(self):
        act_id = uuid.uuid4()
        item = self._FakeItem(id=uuid.uuid4(), activity_id=act_id, description="Steel beam")
        result = identify_critical_materials([item], critical_activity_ids={act_id})
        assert len(result) == 1
        assert result[0].activity_id == act_id

    def test_item_not_on_critical_path_excluded(self):
        item = self._FakeItem(id=uuid.uuid4(), activity_id=uuid.uuid4(), description="Bolt")
        result = identify_critical_materials([item], critical_activity_ids={uuid.uuid4()})
        assert result == []

    def test_item_with_no_activity_id_excluded(self):
        item = self._FakeItem(id=uuid.uuid4(), activity_id=None, description="Misc")
        result = identify_critical_materials([item], critical_activity_ids={uuid.uuid4()})
        assert result == []

    def test_returns_critical_material_info_instances(self):
        act_id = uuid.uuid4()
        item = self._FakeItem(id=uuid.uuid4(), activity_id=act_id, description="Pipe section")
        result = identify_critical_materials([item], critical_activity_ids={act_id})
        assert isinstance(result[0], CriticalMaterialInfo)

    def test_description_stored_in_result(self):
        act_id = uuid.uuid4()
        item = self._FakeItem(id=uuid.uuid4(), activity_id=act_id, description="Foundation bolt")
        result = identify_critical_materials([item], critical_activity_ids={act_id})
        assert result[0].description == "Foundation bolt"

    def test_material_item_id_stored(self):
        act_id = uuid.uuid4()
        item_id = uuid.uuid4()
        item = self._FakeItem(id=item_id, activity_id=act_id, description="X")
        result = identify_critical_materials([item], critical_activity_ids={act_id})
        assert result[0].material_item_id == item_id

    def test_mixed_items_only_critical_returned(self):
        critical_act = uuid.uuid4()
        non_critical_act = uuid.uuid4()
        items = [
            self._FakeItem(id=uuid.uuid4(), activity_id=critical_act, description="Critical item"),
            self._FakeItem(id=uuid.uuid4(), activity_id=non_critical_act, description="Non-critical"),
            self._FakeItem(id=uuid.uuid4(), activity_id=None, description="No activity"),
        ]
        result = identify_critical_materials(items, critical_activity_ids={critical_act})
        assert len(result) == 1
        assert result[0].description == "Critical item"

    def test_multiple_critical_items_all_returned(self):
        act1 = uuid.uuid4()
        act2 = uuid.uuid4()
        items = [
            self._FakeItem(id=uuid.uuid4(), activity_id=act1, description="Item A"),
            self._FakeItem(id=uuid.uuid4(), activity_id=act2, description="Item B"),
        ]
        result = identify_critical_materials(items, critical_activity_ids={act1, act2})
        assert len(result) == 2
