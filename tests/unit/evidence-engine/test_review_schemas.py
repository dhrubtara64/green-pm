"""Unit tests for Evidence Review schemas — S4-01."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.reviews.schemas import EvidenceReviewCreate, EvidenceReviewResponse


# ──────────────────────────────────────────────────────────────────────────────
# EvidenceReviewCreate
# ──────────────────────────────────────────────────────────────────────────────

class TestEvidenceReviewCreate:
    def test_approved_outcome_accepted(self):
        r = EvidenceReviewCreate(outcome="approved")
        assert r.outcome == "approved"

    def test_rejected_outcome_accepted(self):
        r = EvidenceReviewCreate(outcome="rejected")
        assert r.outcome == "rejected"

    def test_needs_revision_outcome_accepted(self):
        r = EvidenceReviewCreate(outcome="needs_revision")
        assert r.outcome == "needs_revision"

    def test_invalid_outcome_raises(self):
        with pytest.raises(ValueError, match="outcome"):
            EvidenceReviewCreate(outcome="pending")

    def test_unknown_outcome_raises(self):
        with pytest.raises(ValueError):
            EvidenceReviewCreate(outcome="maybe")

    def test_comments_optional(self):
        r = EvidenceReviewCreate(outcome="approved")
        assert r.comments is None

    def test_comments_accepted(self):
        r = EvidenceReviewCreate(outcome="approved", comments="Good quality photo.")
        assert r.comments == "Good quality photo."

    def test_comments_max_length(self):
        long = "x" * 4000
        r = EvidenceReviewCreate(outcome="approved", comments=long)
        assert len(r.comments) == 4000

    def test_comments_too_long_raises(self):
        with pytest.raises(ValueError):
            EvidenceReviewCreate(outcome="approved", comments="x" * 4001)

    def test_reliability_weight_defaults_to_one(self):
        r = EvidenceReviewCreate(outcome="approved")
        assert r.reliability_weight == 1.0

    def test_reliability_weight_zero_accepted(self):
        r = EvidenceReviewCreate(outcome="approved", reliability_weight=0.0)
        assert r.reliability_weight == 0.0

    def test_reliability_weight_fractional(self):
        r = EvidenceReviewCreate(outcome="approved", reliability_weight=0.75)
        assert r.reliability_weight == 0.75

    def test_reliability_weight_above_one_raises(self):
        with pytest.raises(ValueError):
            EvidenceReviewCreate(outcome="approved", reliability_weight=1.01)

    def test_reliability_weight_below_zero_raises(self):
        with pytest.raises(ValueError):
            EvidenceReviewCreate(outcome="approved", reliability_weight=-0.01)

    def test_all_fields(self):
        r = EvidenceReviewCreate(
            outcome="rejected",
            comments="Image is blurry.",
            reliability_weight=0.5,
        )
        assert r.outcome == "rejected"
        assert r.comments == "Image is blurry."
        assert r.reliability_weight == 0.5


# ──────────────────────────────────────────────────────────────────────────────
# EvidenceReviewResponse
# ──────────────────────────────────────────────────────────────────────────────

class TestEvidenceReviewResponse:
    def _base(self):
        now = datetime.now(timezone.utc)
        return {
            "id": uuid.uuid4(),
            "evidence_id": uuid.uuid4(),
            "reviewer_id": uuid.uuid4(),
            "outcome": "approved",
            "comments": None,
            "reviewed_at": now,
            "reliability_weight": Decimal("1.00"),
            "created_at": now,
        }

    def test_from_dict(self):
        r = EvidenceReviewResponse(**self._base())
        assert r.outcome == "approved"

    def test_id_is_uuid(self):
        r = EvidenceReviewResponse(**self._base())
        assert isinstance(r.id, uuid.UUID)

    def test_comments_none(self):
        r = EvidenceReviewResponse(**self._base())
        assert r.comments is None

    def test_from_attributes_config(self):
        assert EvidenceReviewResponse.model_config.get("from_attributes") is True

    def test_reliability_weight_decimal(self):
        r = EvidenceReviewResponse(**self._base())
        assert isinstance(r.reliability_weight, Decimal)

    def test_all_outcome_values(self):
        for outcome in ("approved", "rejected", "needs_revision"):
            base = self._base()
            base["outcome"] = outcome
            r = EvidenceReviewResponse(**base)
            assert r.outcome == outcome
