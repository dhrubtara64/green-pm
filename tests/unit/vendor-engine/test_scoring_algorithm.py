"""Tests for vendor scoring algorithms — S8-01, S8-02, S8-03."""
import uuid
from datetime import datetime, timezone

import pytest

from app.scoring.algorithm import (
    build_causal_attribution,
    compute_trend,
    compute_vendor_score,
)
from app.scoring.schemas import (
    _DEFAULT_WEIGHTS,
    _TREND_THRESHOLD,
    CausalAttribution,
    DimensionScores,
    ReliabilityPrediction,
    VendorScore,
)


def _ds(**overrides) -> DimensionScores:
    defaults = dict(
        quality=80.0, delivery=80.0, responsiveness=80.0,
        documentation=80.0, commercial=80.0, relationship=80.0,
    )
    return DimensionScores(**{**defaults, **overrides})


def _uniform(score: float) -> DimensionScores:
    return _ds(quality=score, delivery=score, responsiveness=score,
               documentation=score, commercial=score, relationship=score)


class TestComputeVendorScore:
    def test_returns_vendor_score_instance(self):
        result = compute_vendor_score(uuid.uuid4(), _uniform(70.0))
        assert isinstance(result, VendorScore)

    def test_equal_dimensions_overall_equals_dimension(self):
        result = compute_vendor_score(uuid.uuid4(), _uniform(75.0))
        assert result.overall_score == pytest.approx(75.0, abs=0.01)

    def test_all_zeros_overall_is_zero(self):
        result = compute_vendor_score(uuid.uuid4(), _uniform(0.0))
        assert result.overall_score == pytest.approx(0.0)

    def test_all_hundreds_overall_is_hundred(self):
        result = compute_vendor_score(uuid.uuid4(), _uniform(100.0))
        assert result.overall_score == pytest.approx(100.0)

    def test_default_weights_applied(self):
        ds = _ds(quality=100.0, delivery=0.0, responsiveness=0.0,
                 documentation=0.0, commercial=0.0, relationship=0.0)
        result = compute_vendor_score(uuid.uuid4(), ds)
        # quality weight = 0.25 → overall = 25.0
        assert result.overall_score == pytest.approx(25.0, abs=0.01)

    def test_custom_weights_applied(self):
        custom_weights = {d: (1.0 / 6) for d in _DEFAULT_WEIGHTS}
        ds = _ds(quality=100.0, delivery=0.0, responsiveness=0.0,
                 documentation=0.0, commercial=0.0, relationship=0.0)
        result = compute_vendor_score(uuid.uuid4(), ds, weights=custom_weights)
        assert result.overall_score == pytest.approx(100.0 / 6, abs=0.1)

    def test_vendor_id_stored(self):
        vid = uuid.uuid4()
        result = compute_vendor_score(vid, _uniform(50.0))
        assert result.vendor_id == vid

    def test_dimension_scores_stored(self):
        ds = _uniform(60.0)
        result = compute_vendor_score(uuid.uuid4(), ds)
        assert result.dimension_scores is ds

    def test_weights_stored(self):
        result = compute_vendor_score(uuid.uuid4(), _uniform(50.0))
        assert result.weights == _DEFAULT_WEIGHTS

    def test_weights_not_summing_to_one_raises(self):
        bad_weights = {d: 0.5 for d in _DEFAULT_WEIGHTS}  # sums to 3.0
        with pytest.raises(ValueError, match="sum"):
            compute_vendor_score(uuid.uuid4(), _uniform(50.0), weights=bad_weights)

    def test_result_rounded_to_two_decimal_places(self):
        # 100 * 0.25 + 0*0.75 = 25.0 exactly; check with asymmetric dimensions
        ds = _ds(quality=33.333, delivery=33.333, responsiveness=33.333,
                 documentation=33.333, commercial=33.333, relationship=33.333)
        result = compute_vendor_score(uuid.uuid4(), ds)
        # Check result has at most 2 decimal places
        assert result.overall_score == round(result.overall_score, 2)

    def test_weighted_average_correct_with_mixed_dimensions(self):
        # weights: quality=0.25, delivery=0.25, rest share 0.5
        ds = _ds(quality=100.0, delivery=0.0, responsiveness=50.0,
                 documentation=50.0, commercial=50.0, relationship=50.0)
        result = compute_vendor_score(uuid.uuid4(), ds)
        # 100*0.25 + 0*0.25 + 50*0.15 + 50*0.10 + 50*0.15 + 50*0.10 = 25+0+7.5+5+7.5+5 = 50.0
        assert result.overall_score == pytest.approx(50.0, abs=0.01)


class TestBuildCausalAttribution:
    def test_returns_causal_attribution(self):
        result = build_causal_attribution(
            "score.updated", uuid.uuid4(), "quality", 70.0, 80.0
        )
        assert isinstance(result, CausalAttribution)

    def test_event_type_stored(self):
        result = build_causal_attribution("rfi.closed", uuid.uuid4(), "responsiveness", 50.0, 60.0)
        assert result.event_type == "rfi.closed"

    def test_event_id_stored(self):
        eid = uuid.uuid4()
        result = build_causal_attribution("score.updated", eid, "delivery", 60.0, 70.0)
        assert result.event_id == eid

    def test_dimension_stored(self):
        result = build_causal_attribution("delivery.completed", uuid.uuid4(), "delivery", 60.0, 80.0)
        assert result.dimension == "delivery"

    def test_positive_delta_on_improvement(self):
        result = build_causal_attribution("score.updated", uuid.uuid4(), "quality", 60.0, 80.0)
        assert result.score_delta == pytest.approx(20.0)

    def test_negative_delta_on_regression(self):
        result = build_causal_attribution("delay.reported", uuid.uuid4(), "delivery", 80.0, 60.0)
        assert result.score_delta == pytest.approx(-20.0)

    def test_zero_delta_when_no_change(self):
        result = build_causal_attribution("noop", uuid.uuid4(), "quality", 75.0, 75.0)
        assert result.score_delta == pytest.approx(0.0)

    def test_recorded_at_defaults_to_utc_now(self):
        result = build_causal_attribution("score.updated", uuid.uuid4(), "quality", 50.0, 60.0)
        assert result.recorded_at is not None

    def test_custom_recorded_at_stored(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = build_causal_attribution(
            "score.updated", uuid.uuid4(), "quality", 50.0, 60.0, recorded_at=ts
        )
        assert result.recorded_at == ts

    def test_delta_rounded_to_four_decimal_places(self):
        result = build_causal_attribution("score.updated", uuid.uuid4(), "quality", 70.0, 80.1234567)
        assert result.score_delta == round(result.score_delta, 4)


class TestComputeTrend:
    def test_empty_history_stable(self):
        result = compute_trend([])
        assert result.direction == "STABLE"

    def test_single_score_stable(self):
        result = compute_trend([75.0])
        assert result.direction == "STABLE"

    def test_single_score_confidence_zero(self):
        result = compute_trend([75.0])
        assert result.confidence == 0.0

    def test_constant_history_stable(self):
        result = compute_trend([70.0, 70.0, 70.0, 70.0])
        assert result.direction == "STABLE"

    def test_rising_history_improving(self):
        # slope = 5/period → > _TREND_THRESHOLD
        history = [60.0, 65.0, 70.0, 75.0, 80.0]
        result = compute_trend(history)
        assert result.direction == "IMPROVING"

    def test_falling_history_declining(self):
        history = [80.0, 75.0, 70.0, 65.0, 60.0]
        result = compute_trend(history)
        assert result.direction == "DECLINING"

    def test_small_variation_stable(self):
        # slope < _TREND_THRESHOLD
        history = [70.0, 70.5, 71.0]
        result = compute_trend(history)
        assert result.direction == "STABLE"

    def test_returns_reliability_prediction_instance(self):
        result = compute_trend([70.0, 72.0])
        assert isinstance(result, ReliabilityPrediction)

    def test_window_size_stored(self):
        history = [70.0, 75.0, 80.0]
        result = compute_trend(history)
        assert result.rolling_window_size == 3

    def test_confidence_increases_with_more_data(self):
        small = compute_trend([70.0, 72.0])
        large = compute_trend([60.0, 62.0, 64.0, 66.0, 68.0, 70.0, 72.0, 74.0, 76.0, 78.0])
        assert large.confidence >= small.confidence

    def test_confidence_max_one_at_ten_points(self):
        result = compute_trend([float(i) * 3 for i in range(10)])
        assert result.confidence <= 1.0

    def test_predicted_score_30d_capped_at_100(self):
        # Strong upward trend from near 100
        history = [90.0, 95.0, 99.0]
        result = compute_trend(history)
        assert result.predicted_score_30d <= 100.0

    def test_predicted_score_30d_capped_at_zero(self):
        # Strong downward trend near 0
        history = [10.0, 5.0, 1.0]
        result = compute_trend(history)
        assert result.predicted_score_30d >= 0.0

    def test_single_point_predicted_equals_that_score(self):
        result = compute_trend([65.0])
        assert result.predicted_score_30d == pytest.approx(65.0)

    def test_empty_history_predicted_is_fifty(self):
        result = compute_trend([])
        assert result.predicted_score_30d == pytest.approx(50.0)
