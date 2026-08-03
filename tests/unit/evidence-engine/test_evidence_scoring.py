"""Unit tests for Evidence Score v5 formula — S3-05.

Tests the 11 invariants from the v5 Test Strategy plus edge-case coverage.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import app.scoring.formula as _formula_mod
from app.scoring.formula import (
    ComputedScore,
    EvidenceItem,
    _30_DAYS_SECONDS,
    _CAPTURE_TYPE_COUNT,
    _RELIABILITY_WEIGHTS,
    compute_evidence_score,
)

_NOW = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)


def _item(
    days_ago: float = 0,
    capture_type: str = "site_photo",
    reliability_tier: str = "secondary",
) -> EvidenceItem:
    captured_at = _NOW - timedelta(days=days_ago)
    return EvidenceItem(
        captured_at=captured_at,
        capture_type=capture_type,
        reliability_tier=reliability_tier,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Empty set
# ──────────────────────────────────────────────────────────────────────────────

class TestEmptySet:
    def test_zero_items_returns_zero_score(self):
        s = compute_evidence_score([], now=_NOW)
        assert s.score_value == 0.0

    def test_zero_items_source_count_zero(self):
        s = compute_evidence_score([], now=_NOW)
        assert s.source_count == 0

    def test_zero_items_all_components_zero(self):
        s = compute_evidence_score([], now=_NOW)
        assert s.recency_decay == 0.0
        assert s.capture_diversity == 0.0
        assert s.reliability_weight_avg == 0.0

    def test_zero_items_corroboration_preserved(self):
        s = compute_evidence_score([], now=_NOW, corroboration_ratio=0.8)
        assert s.corroboration_ratio == 0.8


# ──────────────────────────────────────────────────────────────────────────────
# Source count component
# ──────────────────────────────────────────────────────────────────────────────

class TestSourceCount:
    def test_single_item_source_count(self):
        s = compute_evidence_score([_item()], now=_NOW)
        assert s.source_count == 1

    def test_ten_items_source_count(self):
        items = [_item() for _ in range(10)]
        s = compute_evidence_score(items, now=_NOW)
        assert s.source_count == 10

    def test_source_count_saturates_at_10(self):
        eleven = [_item() for _ in range(11)]
        ten = [_item() for _ in range(10)]
        s11 = compute_evidence_score(eleven, now=_NOW)
        s10 = compute_evidence_score(ten, now=_NOW)
        assert s11.source_count == 11
        # But source component contribution is equal (capped at 10)
        assert abs(s11.score_value - s10.score_value) < 1e-9

    def test_100_items_score_equals_10_items(self):
        many = [_item() for _ in range(100)]
        ten = [_item() for _ in range(10)]
        s_many = compute_evidence_score(many, now=_NOW)
        s_ten = compute_evidence_score(ten, now=_NOW)
        assert abs(s_many.score_value - s_ten.score_value) < 1e-9


# ──────────────────────────────────────────────────────────────────────────────
# Recency decay component
# ──────────────────────────────────────────────────────────────────────────────

class TestRecencyDecay:
    def test_fresh_item_decay_is_one(self):
        s = compute_evidence_score([_item(days_ago=0)], now=_NOW)
        assert s.recency_decay == pytest.approx(1.0, abs=0.001)

    def test_30_day_old_item_decay_is_zero(self):
        s = compute_evidence_score([_item(days_ago=30)], now=_NOW)
        assert s.recency_decay == pytest.approx(0.0, abs=0.001)

    def test_older_than_30_days_clamps_to_zero(self):
        s = compute_evidence_score([_item(days_ago=60)], now=_NOW)
        assert s.recency_decay == 0.0

    def test_15_day_old_item_decay_is_half(self):
        s = compute_evidence_score([_item(days_ago=15)], now=_NOW)
        assert s.recency_decay == pytest.approx(0.5, abs=0.005)

    def test_recency_averages_across_items(self):
        fresh = _item(days_ago=0)
        stale = _item(days_ago=30)
        s = compute_evidence_score([fresh, stale], now=_NOW)
        assert s.recency_decay == pytest.approx(0.5, abs=0.005)

    def test_naive_datetime_treated_as_utc(self):
        naive_item = EvidenceItem(
            captured_at=_NOW.replace(tzinfo=None),
            capture_type="site_photo",
            reliability_tier="secondary",
        )
        s = compute_evidence_score([naive_item], now=_NOW)
        assert s.recency_decay == pytest.approx(1.0, abs=0.001)


# ──────────────────────────────────────────────────────────────────────────────
# Corroboration ratio
# ──────────────────────────────────────────────────────────────────────────────

class TestCorroborationRatio:
    def test_default_corroboration_is_one(self):
        s = compute_evidence_score([_item()], now=_NOW)
        assert s.corroboration_ratio == 1.0

    def test_corroboration_passed_through(self):
        s = compute_evidence_score([_item()], now=_NOW, corroboration_ratio=0.75)
        assert s.corroboration_ratio == 0.75

    def test_corroboration_clamped_above_one(self):
        s = compute_evidence_score([_item()], now=_NOW, corroboration_ratio=1.5)
        assert s.corroboration_ratio == 1.0

    def test_corroboration_clamped_below_zero(self):
        s = compute_evidence_score([_item()], now=_NOW, corroboration_ratio=-0.1)
        assert s.corroboration_ratio == 0.0

    def test_zero_corroboration_reduces_score(self):
        s_full = compute_evidence_score([_item()], now=_NOW, corroboration_ratio=1.0)
        s_zero = compute_evidence_score([_item()], now=_NOW, corroboration_ratio=0.0)
        assert s_full.score_value > s_zero.score_value


# ──────────────────────────────────────────────────────────────────────────────
# Capture diversity
# ──────────────────────────────────────────────────────────────────────────────

class TestCaptureDiversity:
    def test_single_type_diversity_is_1_of_12(self):
        items = [_item(capture_type="site_photo") for _ in range(5)]
        s = compute_evidence_score(items, now=_NOW)
        assert s.capture_diversity == pytest.approx(1 / _CAPTURE_TYPE_COUNT, abs=0.001)

    def test_two_types_diversity_is_2_of_12(self):
        items = [_item(capture_type="site_photo"), _item(capture_type="voice_memo")]
        s = compute_evidence_score(items, now=_NOW)
        assert s.capture_diversity == pytest.approx(2 / _CAPTURE_TYPE_COUNT, abs=0.001)

    def test_all_12_types_diversity_is_one(self):
        capture_types = [
            "site_photo", "site_video", "voice_memo", "document_upload",
            "qr_scan", "form_submission", "iot_sensor", "drone_image",
            "surveyor_report", "inspection_report", "weather_log", "financial_document",
        ]
        items = [_item(capture_type=ct) for ct in capture_types]
        s = compute_evidence_score(items, now=_NOW)
        assert s.capture_diversity == pytest.approx(1.0, abs=0.001)

    def test_capture_type_count_is_12(self):
        assert _CAPTURE_TYPE_COUNT == 12


# ──────────────────────────────────────────────────────────────────────────────
# Reliability weight average
# ──────────────────────────────────────────────────────────────────────────────

class TestReliabilityWeightAvg:
    def test_all_primary_reliability_is_one(self):
        items = [_item(reliability_tier="primary") for _ in range(3)]
        s = compute_evidence_score(items, now=_NOW)
        assert s.reliability_weight_avg == pytest.approx(1.0, abs=0.001)

    def test_all_secondary_reliability_is_07(self):
        items = [_item(reliability_tier="secondary") for _ in range(3)]
        s = compute_evidence_score(items, now=_NOW)
        assert s.reliability_weight_avg == pytest.approx(0.7, abs=0.001)

    def test_all_tertiary_reliability_is_02(self):
        items = [_item(reliability_tier="tertiary") for _ in range(3)]
        s = compute_evidence_score(items, now=_NOW)
        assert s.reliability_weight_avg == pytest.approx(0.2, abs=0.001)

    def test_mixed_reliability_averages_correctly(self):
        items = [
            _item(reliability_tier="primary"),    # 1.0
            _item(reliability_tier="secondary"),  # 0.7
            _item(reliability_tier="tertiary"),   # 0.2
        ]
        s = compute_evidence_score(items, now=_NOW)
        expected = (1.0 + 0.7 + 0.2) / 3
        assert s.reliability_weight_avg == pytest.approx(expected, abs=0.001)

    def test_unknown_tier_treated_as_02(self):
        item = EvidenceItem(
            captured_at=_NOW,
            capture_type="site_photo",
            reliability_tier="unverified",  # not in ENUM, graceful fallback
        )
        s = compute_evidence_score([item], now=_NOW)
        assert s.reliability_weight_avg == pytest.approx(0.2, abs=0.001)

    def test_reliability_weights_mapping(self):
        assert _RELIABILITY_WEIGHTS["primary"] == 1.0
        assert _RELIABILITY_WEIGHTS["secondary"] == 0.7
        assert _RELIABILITY_WEIGHTS["tertiary"] == 0.2


# ──────────────────────────────────────────────────────────────────────────────
# Composite score properties
# ──────────────────────────────────────────────────────────────────────────────

class TestCompositeScore:
    def test_score_never_exceeds_one(self):
        items = [
            _item(days_ago=0, capture_type=ct, reliability_tier="primary")
            for ct in [
                "site_photo", "site_video", "voice_memo", "document_upload",
                "qr_scan", "form_submission", "iot_sensor", "drone_image",
                "surveyor_report", "inspection_report", "weather_log", "financial_document",
            ]
        ] * 10
        s = compute_evidence_score(items, now=_NOW, corroboration_ratio=1.0)
        assert s.score_value <= 1.0

    def test_score_never_below_zero(self):
        items = [_item(days_ago=60, reliability_tier="tertiary")]
        s = compute_evidence_score(items, now=_NOW, corroboration_ratio=0.0)
        assert s.score_value >= 0.0

    def test_perfect_evidence_scores_max(self):
        capture_types = [
            "site_photo", "site_video", "voice_memo", "document_upload",
            "qr_scan", "form_submission", "iot_sensor", "drone_image",
            "surveyor_report", "inspection_report", "weather_log", "financial_document",
        ]
        items = [
            _item(days_ago=0, capture_type=ct, reliability_tier="primary")
            for ct in capture_types
        ]
        s = compute_evidence_score(items, now=_NOW, corroboration_ratio=1.0)
        assert s.score_value == pytest.approx(1.0, abs=0.001)

    def test_score_increases_with_more_items(self):
        one = compute_evidence_score([_item()], now=_NOW)
        five = compute_evidence_score([_item() for _ in range(5)], now=_NOW)
        assert five.score_value >= one.score_value

    def test_score_decreases_with_older_items(self):
        fresh = compute_evidence_score([_item(days_ago=0)], now=_NOW)
        old = compute_evidence_score([_item(days_ago=29)], now=_NOW)
        assert fresh.score_value > old.score_value

    def test_higher_reliability_increases_score(self):
        primary = compute_evidence_score([_item(reliability_tier="primary")], now=_NOW)
        tertiary = compute_evidence_score([_item(reliability_tier="tertiary")], now=_NOW)
        assert primary.score_value > tertiary.score_value

    def test_formula_weights_sum_to_one(self):
        total = (
            _formula_mod._W_SOURCE
            + _formula_mod._W_RECENCY
            + _formula_mod._W_CORROBORATION
            + _formula_mod._W_DIVERSITY
            + _formula_mod._W_RELIABILITY
        )
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_computed_score_is_frozen_dataclass(self):
        s = compute_evidence_score([_item()], now=_NOW)
        with pytest.raises((AttributeError, TypeError)):
            s.score_value = 0.5  # type: ignore[misc]

    def test_score_value_rounded_to_3_decimal_places(self):
        items = [_item(days_ago=7.3, reliability_tier="secondary")]
        s = compute_evidence_score(items, now=_NOW)
        assert s.score_value == round(s.score_value, 3)

    def test_known_value_regression(self):
        # 1 item, fresh, single type, secondary, corroboration=1.0
        # source_component = 1/10 × 0.25 = 0.025
        # recency = 1.0 × 0.25 = 0.250
        # corroboration = 1.0 × 0.25 = 0.250
        # diversity = 1/12 × 0.15 ≈ 0.0125
        # reliability = 0.7 × 0.10 = 0.070
        # total ≈ 0.6075
        item = EvidenceItem(
            captured_at=_NOW,
            capture_type="site_photo",
            reliability_tier="secondary",
        )
        s = compute_evidence_score([item], now=_NOW)
        expected = (1 / 10) * 0.25 + 1.0 * 0.25 + 1.0 * 0.25 + (1 / 12) * 0.15 + 0.7 * 0.10
        assert s.score_value == pytest.approx(expected, abs=0.001)
