"""Tests for vendor scoring domain schemas and constants — S8-01, S8-02, S8-03."""
import uuid
from datetime import datetime, timezone

import pytest

from app.scoring.schemas import (
    _DEFAULT_WEIGHTS,
    _DIMENSIONS,
    _TREND_DIRECTIONS,
    _TREND_THRESHOLD,
    CausalAttribution,
    DimensionScores,
    ReliabilityPrediction,
    VendorScore,
)


class TestConstants:
    def test_dimensions_has_six(self):
        assert len(_DIMENSIONS) == 6

    def test_dimensions_contains_all_six(self):
        assert set(_DIMENSIONS) == {
            "quality", "delivery", "responsiveness",
            "documentation", "commercial", "relationship",
        }

    def test_default_weights_has_six_keys(self):
        assert len(_DEFAULT_WEIGHTS) == 6

    def test_default_weights_sum_to_one(self):
        assert abs(sum(_DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9

    def test_default_weights_cover_all_dimensions(self):
        assert set(_DEFAULT_WEIGHTS.keys()) == set(_DIMENSIONS)

    def test_trend_threshold_positive(self):
        assert _TREND_THRESHOLD > 0

    def test_trend_directions_has_three(self):
        assert _TREND_DIRECTIONS == frozenset({"IMPROVING", "STABLE", "DECLINING"})


class TestDimensionScores:
    def _make(self, **overrides) -> DimensionScores:
        defaults = dict(
            quality=80.0, delivery=75.0, responsiveness=70.0,
            documentation=65.0, commercial=60.0, relationship=55.0,
        )
        return DimensionScores(**{**defaults, **overrides})

    def test_stores_all_six_dimensions(self):
        ds = self._make()
        assert ds.quality == 80.0
        assert ds.delivery == 75.0
        assert ds.responsiveness == 70.0
        assert ds.documentation == 65.0
        assert ds.commercial == 60.0
        assert ds.relationship == 55.0

    def test_frozen_immutable(self):
        ds = self._make()
        with pytest.raises((AttributeError, TypeError)):
            ds.quality = 99.0

    def test_zero_scores_valid(self):
        ds = self._make(quality=0.0, delivery=0.0, responsiveness=0.0,
                        documentation=0.0, commercial=0.0, relationship=0.0)
        assert ds.quality == 0.0

    def test_hundred_scores_valid(self):
        ds = self._make(quality=100.0, delivery=100.0, responsiveness=100.0,
                        documentation=100.0, commercial=100.0, relationship=100.0)
        assert ds.quality == 100.0

    def test_negative_quality_raises(self):
        with pytest.raises(ValueError):
            self._make(quality=-1.0)

    def test_over_hundred_delivery_raises(self):
        with pytest.raises(ValueError):
            self._make(delivery=100.1)

    def test_negative_responsiveness_raises(self):
        with pytest.raises(ValueError):
            self._make(responsiveness=-0.01)

    def test_as_dict_has_all_keys(self):
        ds = self._make()
        d = ds.as_dict()
        assert set(d.keys()) == set(_DIMENSIONS)

    def test_as_dict_values_correct(self):
        ds = self._make(quality=90.0)
        assert ds.as_dict()["quality"] == 90.0


class TestVendorScore:
    def _make(self) -> VendorScore:
        ds = DimensionScores(
            quality=80.0, delivery=75.0, responsiveness=70.0,
            documentation=65.0, commercial=60.0, relationship=55.0,
        )
        return VendorScore(
            vendor_id=uuid.uuid4(),
            dimension_scores=ds,
            overall_score=72.5,
            weights=dict(_DEFAULT_WEIGHTS),
        )

    def test_stores_vendor_id(self):
        vid = uuid.uuid4()
        ds = DimensionScores(quality=50.0, delivery=50.0, responsiveness=50.0,
                              documentation=50.0, commercial=50.0, relationship=50.0)
        vs = VendorScore(vendor_id=vid, dimension_scores=ds, overall_score=50.0,
                         weights=dict(_DEFAULT_WEIGHTS))
        assert vs.vendor_id == vid

    def test_stores_overall_score(self):
        vs = self._make()
        assert vs.overall_score == 72.5

    def test_frozen_immutable(self):
        vs = self._make()
        with pytest.raises((AttributeError, TypeError)):
            vs.overall_score = 99.0

    def test_as_dict_has_vendor_id(self):
        vs = self._make()
        d = vs.as_dict()
        assert "vendor_id" in d

    def test_as_dict_has_overall_score(self):
        vs = self._make()
        assert "overall_score" in vs.as_dict()

    def test_as_dict_dimension_scores_is_dict(self):
        vs = self._make()
        assert isinstance(vs.as_dict()["dimension_scores"], dict)

    def test_as_dict_weights_is_dict(self):
        vs = self._make()
        assert isinstance(vs.as_dict()["weights"], dict)


class TestCausalAttribution:
    def _make(self) -> CausalAttribution:
        return CausalAttribution(
            event_type="score.updated",
            event_id=uuid.uuid4(),
            dimension="quality",
            score_delta=5.0,
            recorded_at=datetime.now(timezone.utc),
        )

    def test_stores_event_type(self):
        ca = self._make()
        assert ca.event_type == "score.updated"

    def test_stores_event_id(self):
        eid = uuid.uuid4()
        ca = CausalAttribution(
            event_type="delivery.updated", event_id=eid,
            dimension="delivery", score_delta=-2.0,
            recorded_at=datetime.now(timezone.utc),
        )
        assert ca.event_id == eid

    def test_stores_dimension(self):
        ca = self._make()
        assert ca.dimension == "quality"

    def test_stores_score_delta(self):
        ca = self._make()
        assert ca.score_delta == 5.0

    def test_negative_delta_valid(self):
        ca = CausalAttribution(
            event_type="delivery.failed", event_id=uuid.uuid4(),
            dimension="delivery", score_delta=-10.0,
            recorded_at=datetime.now(timezone.utc),
        )
        assert ca.score_delta == -10.0

    def test_frozen_immutable(self):
        ca = self._make()
        with pytest.raises((AttributeError, TypeError)):
            ca.score_delta = 99.0


class TestReliabilityPrediction:
    def _make(self, direction="STABLE") -> ReliabilityPrediction:
        return ReliabilityPrediction(
            direction=direction,
            predicted_score_30d=72.0,
            rolling_window_size=5,
            confidence=0.5,
        )

    def test_improving_direction_valid(self):
        rp = self._make("IMPROVING")
        assert rp.direction == "IMPROVING"

    def test_stable_direction_valid(self):
        rp = self._make("STABLE")
        assert rp.direction == "STABLE"

    def test_declining_direction_valid(self):
        rp = self._make("DECLINING")
        assert rp.direction == "DECLINING"

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            ReliabilityPrediction(
                direction="UNKNOWN", predicted_score_30d=50.0,
                rolling_window_size=5, confidence=0.5,
            )

    def test_stores_predicted_score(self):
        rp = self._make()
        assert rp.predicted_score_30d == 72.0

    def test_stores_window_size(self):
        rp = self._make()
        assert rp.rolling_window_size == 5

    def test_confidence_zero_valid(self):
        rp = ReliabilityPrediction(direction="STABLE", predicted_score_30d=50.0,
                                   rolling_window_size=0, confidence=0.0)
        assert rp.confidence == 0.0

    def test_confidence_one_valid(self):
        rp = ReliabilityPrediction(direction="STABLE", predicted_score_30d=50.0,
                                   rolling_window_size=10, confidence=1.0)
        assert rp.confidence == 1.0

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError):
            ReliabilityPrediction(direction="STABLE", predicted_score_30d=50.0,
                                  rolling_window_size=5, confidence=1.1)

    def test_frozen_immutable(self):
        rp = self._make()
        with pytest.raises((AttributeError, TypeError)):
            rp.direction = "IMPROVING"
