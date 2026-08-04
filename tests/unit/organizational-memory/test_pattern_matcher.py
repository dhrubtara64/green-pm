"""Tests for pure pattern-matching functions — S13-05, S13-06."""
import uuid
from unittest.mock import MagicMock

import pytest

from app.memory.pattern_matcher import find_matching_patterns, score_pattern_relevance
from app.memory.schemas import PatternMatch


def _mock_pattern(
    pattern_name: str = "Vendor delay",
    category: str = "VENDOR",
    confidence_score: float = 0.8,
    historical_outcomes: list | None = None,
    trigger_conditions: dict | None = None,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.pattern_name = pattern_name
    p.category = category
    p.confidence_score = confidence_score
    p.historical_outcomes = historical_outcomes or []
    p.trigger_conditions = trigger_conditions
    return p


class TestScorePatternRelevance:
    def test_no_keywords_returns_zero(self):
        p = _mock_pattern()
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, []
        )
        assert score == 0.0

    def test_no_match_returns_zero(self):
        p = _mock_pattern(pattern_name="Vendor delay")
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, ["budget", "schedule"]
        )
        assert score == 0.0

    def test_full_match_returns_confidence(self):
        p = _mock_pattern(pattern_name="delay", confidence_score=0.8)
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, ["delay"]
        )
        assert score == pytest.approx(0.8, abs=1e-4)

    def test_partial_match_scales_score(self):
        p = _mock_pattern(pattern_name="vendor delay risk", confidence_score=1.0)
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, ["vendor", "cost"]
        )
        # 1 of 2 keywords matched → 0.5 overlap × 1.0 confidence = 0.5
        assert score == pytest.approx(0.5, abs=1e-4)

    def test_case_insensitive(self):
        p = _mock_pattern(pattern_name="Vendor Delay", confidence_score=0.9)
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, ["vendor"]
        )
        assert score > 0.0

    def test_trigger_conditions_searched(self):
        p = _mock_pattern(
            pattern_name="Pattern",
            confidence_score=0.8,
            trigger_conditions={"type": "supply_shortage"},
        )
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, ["supply_shortage"]
        )
        assert score > 0.0

    def test_none_trigger_conditions_handled(self):
        p = _mock_pattern(pattern_name="delay", trigger_conditions=None)
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, None, ["delay"]
        )
        assert score > 0.0

    def test_returns_float(self):
        p = _mock_pattern()
        score = score_pattern_relevance(
            p.id, p.pattern_name, p.category, p.confidence_score,
            p.historical_outcomes, p.trigger_conditions, ["delay"]
        )
        assert isinstance(score, float)


class TestFindMatchingPatterns:
    def test_empty_patterns_returns_empty(self):
        result = find_matching_patterns([], ["delay"])
        assert result == []

    def test_no_keywords_returns_empty(self):
        p = _mock_pattern(pattern_name="delay")
        result = find_matching_patterns([p], [])
        assert result == []

    def test_returns_list_of_pattern_match(self):
        p = _mock_pattern(pattern_name="vendor delay", category="VENDOR")
        result = find_matching_patterns([p], ["vendor"])
        assert all(isinstance(m, PatternMatch) for m in result)

    def test_matching_pattern_returned(self):
        p = _mock_pattern(pattern_name="vendor delay", category="VENDOR")
        result = find_matching_patterns([p], ["vendor"])
        assert len(result) == 1

    def test_non_matching_pattern_excluded(self):
        p = _mock_pattern(pattern_name="supply shortage", category="VENDOR")
        result = find_matching_patterns([p], ["budget"])
        assert result == []

    def test_sorted_by_relevance_desc(self):
        p1 = _mock_pattern(pattern_name="vendor delay cost", confidence_score=0.8)
        p2 = _mock_pattern(pattern_name="vendor delay", confidence_score=0.8)
        result = find_matching_patterns([p1, p2], ["vendor", "delay", "cost"])
        assert result[0].relevance_score >= result[1].relevance_score

    def test_top_k_limits_results(self):
        patterns = [_mock_pattern(pattern_name=f"vendor delay {i}") for i in range(10)]
        result = find_matching_patterns(patterns, ["vendor"], top_k=3)
        assert len(result) <= 3

    def test_category_filter_applied(self):
        p_vendor = _mock_pattern(pattern_name="vendor delay", category="VENDOR")
        p_risk = _mock_pattern(pattern_name="risk delay", category="RISK")
        result = find_matching_patterns([p_vendor, p_risk], ["delay"], category="VENDOR")
        assert all(m.category == "VENDOR" for m in result)

    def test_category_filter_none_returns_all_matching(self):
        p_vendor = _mock_pattern(pattern_name="delay vendor", category="VENDOR")
        p_risk = _mock_pattern(pattern_name="delay risk", category="RISK")
        result = find_matching_patterns([p_vendor, p_risk], ["delay"], category=None)
        assert len(result) == 2

    def test_pattern_match_fields_set_correctly(self):
        pid = uuid.uuid4()
        p = _mock_pattern(pattern_name="vendor delay", category="VENDOR",
                           confidence_score=0.9, historical_outcomes=["outcome_a"])
        p.id = pid
        result = find_matching_patterns([p], ["vendor"])
        assert result[0].pattern_id == pid
        assert result[0].pattern_name == "vendor delay"
        assert result[0].category == "VENDOR"
        assert result[0].confidence_score == 0.9
        assert "outcome_a" in result[0].historical_outcomes

    def test_none_historical_outcomes_gives_empty_tuple(self):
        p = _mock_pattern(pattern_name="vendor delay", historical_outcomes=None)
        result = find_matching_patterns([p], ["vendor"])
        assert result[0].historical_outcomes == ()

    def test_multiple_keywords_all_matched_higher_score(self):
        p = _mock_pattern(pattern_name="vendor delay risk", confidence_score=1.0)
        # All 3 keywords match → overlap 3/3 = 1.0
        result_full = find_matching_patterns([p], ["vendor", "delay", "risk"])
        # Only 1 of 2 keywords matches → overlap 1/2 = 0.5
        result_partial = find_matching_patterns([p], ["vendor", "budget"])
        assert result_full[0].relevance_score > result_partial[0].relevance_score
