"""Tests for Recommendation Engine schemas — S16-01."""
import uuid

import pytest
from pydantic import ValidationError

from app.recommendation.schemas import (
    SUPPORTED_ENGINES,
    RecommendationCreate,
    RecommendationResponse,
    RecommendationSignal,
    RecommendationStatusUpdate,
    _SIGNAL_TYPES,
    _STATUSES,
)

VALID_ENGINE = "risk-engine"
VALID_SIGNAL = "RISK"
VALID_SCORE = 0.75


class TestSupportedEngines:
    def test_has_sixteen_engines(self):
        assert len(SUPPORTED_ENGINES) == 16

    def test_risk_engine_present(self):
        assert "risk-engine" in SUPPORTED_ENGINES

    def test_evidence_engine_present(self):
        assert "evidence-engine" in SUPPORTED_ENGINES

    def test_core_platform_present(self):
        assert "core-platform" in SUPPORTED_ENGINES

    def test_pig_service_present(self):
        assert "pig-service" in SUPPORTED_ENGINES

    def test_all_engines_are_strings(self):
        assert all(isinstance(e, str) for e in SUPPORTED_ENGINES)

    def test_is_frozenset(self):
        assert isinstance(SUPPORTED_ENGINES, frozenset)


class TestSignalTypes:
    def test_risk_present(self):
        assert "RISK" in _SIGNAL_TYPES

    def test_general_present(self):
        assert "GENERAL" in _SIGNAL_TYPES

    def test_at_least_ten_types(self):
        assert len(_SIGNAL_TYPES) >= 10

    def test_is_frozenset(self):
        assert isinstance(_SIGNAL_TYPES, frozenset)


class TestRecommendationSignal:
    def _make(self, **kwargs):
        defaults = dict(
            engine_name=VALID_ENGINE,
            signal_type=VALID_SIGNAL,
            priority_score=VALID_SCORE,
            entity_id=uuid.uuid4(),
            title="Review vendor KPIs",
            description="Vendor performance below threshold",
        )
        defaults.update(kwargs)
        return RecommendationSignal(**defaults)

    def test_creates_successfully(self):
        sig = self._make()
        assert sig.engine_name == VALID_ENGINE

    def test_is_frozen(self):
        sig = self._make()
        with pytest.raises((AttributeError, TypeError)):
            sig.priority_score = 0.1  # type: ignore[misc]

    def test_engine_name_stored(self):
        sig = self._make(engine_name="vendor-engine")
        assert sig.engine_name == "vendor-engine"

    def test_signal_type_stored(self):
        sig = self._make(signal_type="VENDOR_ISSUE")
        assert sig.signal_type == "VENDOR_ISSUE"

    def test_priority_score_stored(self):
        sig = self._make(priority_score=0.5)
        assert sig.priority_score == pytest.approx(0.5)

    def test_priority_score_zero_valid(self):
        sig = self._make(priority_score=0.0)
        assert sig.priority_score == pytest.approx(0.0)

    def test_priority_score_one_valid(self):
        sig = self._make(priority_score=1.0)
        assert sig.priority_score == pytest.approx(1.0)

    def test_invalid_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            self._make(engine_name="ghost-engine")

    def test_invalid_signal_type_raises(self):
        with pytest.raises(ValueError, match="Invalid signal_type"):
            self._make(signal_type="UNKNOWN_TYPE")

    def test_priority_score_below_zero_raises(self):
        with pytest.raises(ValueError):
            self._make(priority_score=-0.01)

    def test_priority_score_above_one_raises(self):
        with pytest.raises(ValueError):
            self._make(priority_score=1.01)

    def test_empty_title_raises(self):
        with pytest.raises(ValueError):
            self._make(title="   ")

    def test_entity_id_stored(self):
        eid = uuid.uuid4()
        sig = self._make(entity_id=eid)
        assert sig.entity_id == eid

    def test_description_stored(self):
        sig = self._make(description="Critical path delay detected")
        assert "delay" in sig.description


class TestRecommendationCreate:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            engine_name=VALID_ENGINE,
            signal_type=VALID_SIGNAL,
            priority_score=VALID_SCORE,
            title="Review vendor KPIs",
            description="Vendor performance below threshold",
        )
        defaults.update(kwargs)
        return RecommendationCreate(**defaults)

    def test_creates_successfully(self):
        rc = self._make()
        assert rc.title == "Review vendor KPIs"

    def test_evidence_ids_defaults_empty(self):
        rc = self._make()
        assert rc.evidence_ids == []

    def test_projected_outcome_defaults_none(self):
        rc = self._make()
        assert rc.projected_outcome is None

    def test_responsible_party_defaults_none(self):
        rc = self._make()
        assert rc.responsible_party is None

    def test_invalid_engine_raises(self):
        with pytest.raises(ValidationError):
            self._make(engine_name="not-a-real-engine")

    def test_invalid_signal_type_raises(self):
        with pytest.raises(ValidationError):
            self._make(signal_type="BOGUS")

    def test_priority_score_below_zero_raises(self):
        with pytest.raises(ValidationError):
            self._make(priority_score=-0.1)

    def test_priority_score_above_one_raises(self):
        with pytest.raises(ValidationError):
            self._make(priority_score=1.1)

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            self._make(title="  ")

    def test_empty_description_raises(self):
        with pytest.raises(ValidationError):
            self._make(description="  ")

    def test_evidence_ids_accepted(self):
        eids = [uuid.uuid4(), uuid.uuid4()]
        rc = self._make(evidence_ids=eids)
        assert len(rc.evidence_ids) == 2

    def test_all_engines_accepted(self):
        for engine in SUPPORTED_ENGINES:
            rc = self._make(engine_name=engine)
            assert rc.engine_name == engine

    def test_all_signal_types_accepted(self):
        for st in _SIGNAL_TYPES:
            rc = self._make(signal_type=st)
            assert rc.signal_type == st

    def test_priority_score_boundary_zero(self):
        rc = self._make(priority_score=0.0)
        assert rc.priority_score == pytest.approx(0.0)

    def test_priority_score_boundary_one(self):
        rc = self._make(priority_score=1.0)
        assert rc.priority_score == pytest.approx(1.0)


class TestRecommendationResponse:
    def _make_dict(self, **kwargs):
        defaults = dict(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            engine_name=VALID_ENGINE,
            signal_type=VALID_SIGNAL,
            priority_score=VALID_SCORE,
            title="Test recommendation",
            description="Test description",
            status="ACTIVE",
        )
        defaults.update(kwargs)
        return defaults

    def test_creates_from_dict(self):
        resp = RecommendationResponse(**self._make_dict())
        assert resp.status == "ACTIVE"

    def test_created_at_defaults_none(self):
        resp = RecommendationResponse(**self._make_dict())
        assert resp.created_at is None

    def test_evidence_ids_defaults_empty(self):
        resp = RecommendationResponse(**self._make_dict())
        assert resp.evidence_ids == []

    def test_from_attributes_config(self):
        assert RecommendationResponse.model_config.get("from_attributes") is True


class TestRecommendationStatusUpdate:
    def test_active_valid(self):
        upd = RecommendationStatusUpdate(status="ACTIVE")
        assert upd.status == "ACTIVE"

    def test_actioned_valid(self):
        upd = RecommendationStatusUpdate(status="ACTIONED")
        assert upd.status == "ACTIONED"

    def test_dismissed_valid(self):
        upd = RecommendationStatusUpdate(status="DISMISSED")
        assert upd.status == "DISMISSED"

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            RecommendationStatusUpdate(status="COMPLETED")
