"""Tests for Recommendation Engine ranking functions — S16-01."""
from types import SimpleNamespace

import pytest

from app.recommendation.ranker import (
    DEFAULT_TOP_N,
    filter_by_minimum_score,
    group_by_signal_type,
    rank_recommendations,
    score_recommendation,
)


def _rec(score: float, signal_type: str = "RISK") -> SimpleNamespace:
    return SimpleNamespace(priority_score=score, signal_type=signal_type)


class TestDefaultTopN:
    def test_default_is_ten(self):
        assert DEFAULT_TOP_N == 10


class TestRankRecommendations:
    def test_empty_list_returns_empty(self):
        assert rank_recommendations([]) == []

    def test_single_item_returned(self):
        recs = [_rec(0.5)]
        result = rank_recommendations(recs)
        assert len(result) == 1

    def test_sorted_descending(self):
        recs = [_rec(0.3), _rec(0.9), _rec(0.5)]
        result = rank_recommendations(recs, top_n=3)
        assert result[0].priority_score == pytest.approx(0.9)
        assert result[1].priority_score == pytest.approx(0.5)
        assert result[2].priority_score == pytest.approx(0.3)

    def test_top_n_truncates(self):
        recs = [_rec(float(i) / 10) for i in range(15)]
        result = rank_recommendations(recs, top_n=5)
        assert len(result) == 5

    def test_top_n_larger_than_list_returns_all(self):
        recs = [_rec(0.5), _rec(0.8)]
        result = rank_recommendations(recs, top_n=100)
        assert len(result) == 2

    def test_top_n_zero_returns_empty(self):
        recs = [_rec(0.5)]
        result = rank_recommendations(recs, top_n=0)
        assert result == []

    def test_top_n_negative_raises(self):
        with pytest.raises(ValueError):
            rank_recommendations([_rec(0.5)], top_n=-1)

    def test_default_top_n_applied(self):
        recs = [_rec(float(i) / 20) for i in range(20)]
        result = rank_recommendations(recs)
        assert len(result) == DEFAULT_TOP_N

    def test_highest_score_is_first(self):
        recs = [_rec(0.1), _rec(1.0), _rec(0.5)]
        result = rank_recommendations(recs, top_n=3)
        assert result[0].priority_score == pytest.approx(1.0)

    def test_ties_preserved(self):
        recs = [_rec(0.5), _rec(0.5)]
        result = rank_recommendations(recs, top_n=2)
        assert len(result) == 2
        assert all(r.priority_score == pytest.approx(0.5) for r in result)

    def test_original_list_not_mutated(self):
        recs = [_rec(0.3), _rec(0.9), _rec(0.1)]
        original_order = [r.priority_score for r in recs]
        rank_recommendations(recs, top_n=3)
        assert [r.priority_score for r in recs] == original_order

    def test_top_n_one_returns_highest(self):
        recs = [_rec(0.2), _rec(0.8), _rec(0.5)]
        result = rank_recommendations(recs, top_n=1)
        assert len(result) == 1
        assert result[0].priority_score == pytest.approx(0.8)


class TestScoreRecommendation:
    def test_base_score_only(self):
        result = score_recommendation(0.5, 0)
        assert result == pytest.approx(0.5)

    def test_evidence_adds_bonus(self):
        result = score_recommendation(0.5, 1)
        assert result > 0.5

    def test_evidence_bonus_two_items(self):
        result = score_recommendation(0.5, 2)
        assert result == pytest.approx(0.54)

    def test_evidence_bonus_capped_at_ten(self):
        no_cap = score_recommendation(0.5, 4)   # 4 * 0.02 = 0.08 < cap
        capped = score_recommendation(0.5, 20)  # would be 0.4 > cap of 0.1
        assert capped == pytest.approx(0.6)
        assert no_cap < capped

    def test_result_clamped_to_one(self):
        result = score_recommendation(0.95, 20)
        assert result == pytest.approx(1.0)

    def test_engine_weight_applied(self):
        result = score_recommendation(0.5, 0, engine_weight=2.0)
        assert result == pytest.approx(1.0)

    def test_engine_weight_less_than_one(self):
        result = score_recommendation(0.8, 0, engine_weight=0.5)
        assert result == pytest.approx(0.4)

    def test_base_score_zero_evidence_bonus_only(self):
        result = score_recommendation(0.0, 5)
        assert result == pytest.approx(0.1)

    def test_base_score_above_one_raises(self):
        with pytest.raises(ValueError):
            score_recommendation(1.1, 0)

    def test_base_score_below_zero_raises(self):
        with pytest.raises(ValueError):
            score_recommendation(-0.1, 0)

    def test_negative_evidence_count_raises(self):
        with pytest.raises(ValueError):
            score_recommendation(0.5, -1)

    def test_zero_engine_weight_raises(self):
        with pytest.raises(ValueError):
            score_recommendation(0.5, 0, engine_weight=0.0)

    def test_negative_engine_weight_raises(self):
        with pytest.raises(ValueError):
            score_recommendation(0.5, 0, engine_weight=-1.0)

    def test_boundary_base_zero(self):
        result = score_recommendation(0.0, 0)
        assert result == pytest.approx(0.0)

    def test_boundary_base_one(self):
        result = score_recommendation(1.0, 0)
        assert result == pytest.approx(1.0)


class TestFilterByMinimumScore:
    def test_empty_list(self):
        assert filter_by_minimum_score([], 0.5) == []

    def test_all_pass(self):
        recs = [_rec(0.7), _rec(0.8), _rec(0.9)]
        result = filter_by_minimum_score(recs, 0.5)
        assert len(result) == 3

    def test_none_pass(self):
        recs = [_rec(0.1), _rec(0.2)]
        result = filter_by_minimum_score(recs, 0.5)
        assert result == []

    def test_some_pass(self):
        recs = [_rec(0.3), _rec(0.6), _rec(0.8)]
        result = filter_by_minimum_score(recs, 0.5)
        assert len(result) == 2

    def test_exact_boundary_passes(self):
        recs = [_rec(0.5)]
        result = filter_by_minimum_score(recs, 0.5)
        assert len(result) == 1

    def test_min_score_zero_returns_all(self):
        recs = [_rec(0.0), _rec(0.5), _rec(1.0)]
        result = filter_by_minimum_score(recs, 0.0)
        assert len(result) == 3

    def test_min_score_above_one_raises(self):
        with pytest.raises(ValueError):
            filter_by_minimum_score([_rec(0.5)], 1.1)

    def test_min_score_below_zero_raises(self):
        with pytest.raises(ValueError):
            filter_by_minimum_score([_rec(0.5)], -0.1)


class TestGroupBySignalType:
    def test_empty_list(self):
        assert group_by_signal_type([]) == {}

    def test_single_type(self):
        recs = [_rec(0.5, "RISK"), _rec(0.8, "RISK")]
        groups = group_by_signal_type(recs)
        assert "RISK" in groups
        assert len(groups["RISK"]) == 2

    def test_multiple_types(self):
        recs = [_rec(0.5, "RISK"), _rec(0.8, "DELAY"), _rec(0.3, "RISK")]
        groups = group_by_signal_type(recs)
        assert len(groups) == 2
        assert len(groups["RISK"]) == 2
        assert len(groups["DELAY"]) == 1

    def test_order_preserved_within_group(self):
        r1 = _rec(0.5, "RISK")
        r2 = _rec(0.9, "RISK")
        groups = group_by_signal_type([r1, r2])
        assert groups["RISK"][0] is r1
        assert groups["RISK"][1] is r2

    def test_returns_dict(self):
        result = group_by_signal_type([_rec(0.5)])
        assert isinstance(result, dict)
