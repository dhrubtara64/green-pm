"""Tests for Organizational Memory Engine schemas — S13-01, S13-05, S13-06."""
import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.memory.schemas import (
    HistoricalContextResponse,
    MemoryPatternResponse,
    MemoryRecordCreate,
    MemoryRecordResponse,
    MemorySearchQuery,
    MemorySearchRequest,
    MemorySearchResponse,
    PatternMatch,
    _MEMORY_CATEGORIES,
)


class TestMemoryCategoriesConstant:
    def test_is_frozenset(self):
        assert isinstance(_MEMORY_CATEGORIES, frozenset)

    def test_has_four_categories(self):
        assert len(_MEMORY_CATEGORIES) == 4

    def test_decision_present(self):
        assert "DECISION" in _MEMORY_CATEGORIES

    def test_vendor_present(self):
        assert "VENDOR" in _MEMORY_CATEGORIES

    def test_risk_present(self):
        assert "RISK" in _MEMORY_CATEGORIES

    def test_schedule_present(self):
        assert "SCHEDULE" in _MEMORY_CATEGORIES


class TestMemorySearchQuery:
    def _make(self, **overrides) -> MemorySearchQuery:
        base = dict(
            category="DECISION",
            context_keywords=("vendor", "delay"),
            top_k=5,
        )
        return MemorySearchQuery(**{**base, **overrides})

    def test_stores_category(self):
        assert self._make().category == "DECISION"

    def test_stores_context_keywords(self):
        q = self._make(context_keywords=("a", "b"))
        assert q.context_keywords == ("a", "b")

    def test_stores_top_k(self):
        assert self._make(top_k=3).top_k == 3

    def test_is_frozen(self):
        q = self._make()
        with pytest.raises(FrozenInstanceError):
            q.category = "RISK"  # type: ignore[misc]

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="category"):
            self._make(category="BOGUS")

    def test_top_k_zero_raises(self):
        with pytest.raises(ValueError, match="top_k"):
            self._make(top_k=0)

    def test_top_k_negative_raises(self):
        with pytest.raises(ValueError, match="top_k"):
            self._make(top_k=-1)

    def test_all_valid_categories(self):
        for cat in _MEMORY_CATEGORIES:
            q = self._make(category=cat)
            assert q.category == cat

    def test_top_k_one_valid(self):
        q = self._make(top_k=1)
        assert q.top_k == 1

    def test_default_top_k_is_five(self):
        q = MemorySearchQuery(category="RISK", context_keywords=("x",))
        assert q.top_k == 5


class TestPatternMatch:
    def _make(self, **overrides) -> PatternMatch:
        base = dict(
            pattern_id=uuid.uuid4(),
            pattern_name="Vendor delay pattern",
            category="VENDOR",
            confidence_score=0.85,
            historical_outcomes=("delayed delivery", "cost overrun"),
            relevance_score=0.72,
        )
        return PatternMatch(**{**base, **overrides})

    def test_stores_pattern_id(self):
        pid = uuid.uuid4()
        m = self._make(pattern_id=pid)
        assert m.pattern_id == pid

    def test_stores_pattern_name(self):
        assert self._make().pattern_name == "Vendor delay pattern"

    def test_stores_category(self):
        assert self._make().category == "VENDOR"

    def test_stores_confidence_score(self):
        assert self._make().confidence_score == 0.85

    def test_stores_historical_outcomes(self):
        m = self._make(historical_outcomes=("outcome1",))
        assert m.historical_outcomes == ("outcome1",)

    def test_stores_relevance_score(self):
        assert self._make().relevance_score == 0.72

    def test_is_frozen(self):
        m = self._make()
        with pytest.raises(FrozenInstanceError):
            m.category = "RISK"  # type: ignore[misc]


class TestMemoryRecordCreate:
    def _pid(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_stores_project_id(self):
        pid = self._pid()
        c = MemoryRecordCreate(project_id=pid, category="DECISION", summary="X")
        assert c.project_id == pid

    def test_stores_category(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="RISK", summary="X")
        assert c.category == "RISK"

    def test_stores_summary(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="VENDOR", summary="Summary text")
        assert c.summary == "Summary text"

    def test_entity_id_optional(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X")
        assert c.entity_id is None

    def test_entity_type_optional(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X")
        assert c.entity_type is None

    def test_context_optional(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X")
        assert c.context is None

    def test_default_confidence_score(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X")
        assert c.confidence_score == 0.5

    def test_confidence_score_stored(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X",
                               confidence_score=0.9)
        assert c.confidence_score == 0.9

    def test_outcome_optional(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X")
        assert c.outcome is None

    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            MemoryRecordCreate(project_id=self._pid(), category="BOGUS", summary="X")

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X",
                               confidence_score=1.1)

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X",
                               confidence_score=-0.1)

    def test_confidence_zero_valid(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X",
                               confidence_score=0.0)
        assert c.confidence_score == 0.0

    def test_confidence_one_valid(self):
        c = MemoryRecordCreate(project_id=self._pid(), category="DECISION", summary="X",
                               confidence_score=1.0)
        assert c.confidence_score == 1.0

    def test_all_valid_categories(self):
        for cat in _MEMORY_CATEGORIES:
            c = MemoryRecordCreate(project_id=self._pid(), category=cat, summary="X")
            assert c.category == cat


class TestMemoryRecordResponse:
    def test_from_attributes_enabled(self):
        assert MemoryRecordResponse.model_config.get("from_attributes") is True

    def test_stores_id(self):
        rid = uuid.uuid4()
        r = MemoryRecordResponse(id=rid, project_id=uuid.uuid4(),
                                 category="DECISION", summary="X", confidence_score=0.5)
        assert r.id == rid

    def test_optional_fields_none_by_default(self):
        r = MemoryRecordResponse(id=uuid.uuid4(), project_id=uuid.uuid4(),
                                 category="DECISION", summary="X", confidence_score=0.5)
        assert r.entity_id is None
        assert r.entity_type is None
        assert r.context is None
        assert r.outcome is None
        assert r.created_at is None


class TestMemoryPatternResponse:
    def test_from_attributes_enabled(self):
        assert MemoryPatternResponse.model_config.get("from_attributes") is True

    def test_stores_pattern_name(self):
        r = MemoryPatternResponse(id=uuid.uuid4(), category="VENDOR",
                                  pattern_name="Delay pattern",
                                  confidence_score=0.8, occurrence_count=3)
        assert r.pattern_name == "Delay pattern"

    def test_optional_fields_none_by_default(self):
        r = MemoryPatternResponse(id=uuid.uuid4(), category="RISK",
                                  pattern_name="P", confidence_score=0.5, occurrence_count=1)
        assert r.project_id is None
        assert r.trigger_conditions is None
        assert r.historical_outcomes is None
        assert r.created_at is None
        assert r.updated_at is None


class TestMemorySearchRequest:
    def test_stores_category(self):
        r = MemorySearchRequest(category="DECISION", context_keywords=["a"])
        assert r.category == "DECISION"

    def test_stores_keywords(self):
        r = MemorySearchRequest(category="VENDOR", context_keywords=["delay", "cost"])
        assert r.context_keywords == ["delay", "cost"]

    def test_default_top_k_is_five(self):
        r = MemorySearchRequest(category="RISK", context_keywords=["x"])
        assert r.top_k == 5

    def test_top_k_stored(self):
        r = MemorySearchRequest(category="SCHEDULE", context_keywords=["x"], top_k=3)
        assert r.top_k == 3

    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            MemorySearchRequest(category="BOGUS", context_keywords=["x"])

    def test_top_k_zero_raises(self):
        with pytest.raises(ValidationError):
            MemorySearchRequest(category="RISK", context_keywords=["x"], top_k=0)


class TestMemorySearchResponse:
    def test_stores_matches_and_total(self):
        r = MemorySearchResponse(matches=[], total=0)
        assert r.total == 0
        assert r.matches == []


class TestHistoricalContextResponse:
    def test_stores_all_fields(self):
        r = HistoricalContextResponse(
            pattern_name="Pattern A",
            category="DECISION",
            confidence_score=0.9,
            historical_outcomes=["outcome1"],
            relevance_score=0.75,
        )
        assert r.pattern_name == "Pattern A"
        assert r.category == "DECISION"
        assert r.confidence_score == 0.9
        assert r.historical_outcomes == ["outcome1"]
        assert r.relevance_score == 0.75
