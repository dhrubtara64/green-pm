"""Unit tests for Evidence Engine schemas — S3-01."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.evidence.schemas import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    _CAPTURE_TYPES,
    _DEFAULT_RELIABILITY,
)

_PROJ = uuid.uuid4()
_ENTITY = uuid.uuid4()


def _make(**kwargs) -> EvidenceCreate:
    defaults = {
        "project_id": _PROJ,
        "entity_type": "activity",
        "entity_id": _ENTITY,
        "capture_type": "site_photo",
    }
    defaults.update(kwargs)
    return EvidenceCreate(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# Capture type validation (12 types)
# ──────────────────────────────────────────────────────────────────────────────

class TestCaptureTypes:
    @pytest.mark.parametrize("ct", sorted(_CAPTURE_TYPES))
    def test_all_12_capture_types_accepted(self, ct: str):
        e = _make(capture_type=ct)
        assert e.capture_type == ct

    def test_unknown_capture_type_rejected(self):
        with pytest.raises(ValidationError, match="Invalid capture_type"):
            _make(capture_type="fingerprint_scan")

    def test_capture_type_case_sensitive(self):
        with pytest.raises(ValidationError):
            _make(capture_type="Site_Photo")

    def test_capture_type_empty_rejected(self):
        with pytest.raises(ValidationError):
            _make(capture_type="")

    def test_12_distinct_capture_types(self):
        assert len(_CAPTURE_TYPES) == 12


# ──────────────────────────────────────────────────────────────────────────────
# Required fields
# ──────────────────────────────────────────────────────────────────────────────

class TestRequiredFields:
    def test_project_id_required(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(
                entity_type="activity",
                entity_id=uuid.uuid4(),
                capture_type="site_photo",
            )

    def test_entity_type_required(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(
                project_id=_PROJ,
                entity_id=_ENTITY,
                capture_type="site_photo",
            )

    def test_entity_id_required(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(
                project_id=_PROJ,
                entity_type="activity",
                capture_type="site_photo",
            )

    def test_capture_type_required(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(
                project_id=_PROJ,
                entity_type="activity",
                entity_id=_ENTITY,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Defaults and normalisation
# ──────────────────────────────────────────────────────────────────────────────

class TestDefaultsAndNormalisation:
    def test_entity_type_lowercased(self):
        e = _make(entity_type="Activity")
        assert e.entity_type == "activity"

    def test_entity_type_stripped(self):
        e = _make(entity_type="  activity  ")
        assert e.entity_type == "activity"

    def test_captured_at_defaults_to_utc_now(self):
        e = _make()
        assert e.captured_at is not None
        assert e.captured_at.tzinfo is not None

    def test_naive_captured_at_gets_utc(self):
        naive = datetime(2026, 6, 1, 10, 0, 0)
        e = _make(captured_at=naive)
        assert e.captured_at.tzinfo == timezone.utc

    def test_metadata_defaults_to_empty_dict(self):
        e = _make()
        assert e.metadata == {}

    def test_reliability_tier_defaults_from_capture_type(self):
        for ct, expected_tier in _DEFAULT_RELIABILITY.items():
            e = _make(capture_type=ct)
            assert e.reliability_tier == expected_tier, f"{ct} → expected {expected_tier}"

    def test_explicit_reliability_tier_overrides_default(self):
        e = _make(capture_type="inspection_report", reliability_tier="tertiary")
        assert e.reliability_tier == "tertiary"


# ──────────────────────────────────────────────────────────────────────────────
# Reliability tier validation
# ──────────────────────────────────────────────────────────────────────────────

class TestReliabilityTier:
    @pytest.mark.parametrize("tier", ["primary", "secondary", "tertiary"])
    def test_valid_tiers_accepted(self, tier: str):
        e = _make(reliability_tier=tier)
        assert e.reliability_tier == tier

    def test_invalid_tier_rejected(self):
        with pytest.raises(ValidationError, match="Invalid reliability_tier"):
            _make(reliability_tier="gold")

    def test_none_tier_resolved_from_capture_type(self):
        e = _make(capture_type="surveyor_report", reliability_tier=None)
        assert e.reliability_tier == "primary"


# ──────────────────────────────────────────────────────────────────────────────
# Optional fields
# ──────────────────────────────────────────────────────────────────────────────

class TestOptionalFields:
    def test_description_max_2000_chars(self):
        e = _make(description="x" * 2000)
        assert len(e.description) == 2000

    def test_description_too_long(self):
        with pytest.raises(ValidationError):
            _make(description="x" * 2001)

    def test_location_lat_bounds(self):
        e = _make(location_lat=90.0)
        assert e.location_lat == 90.0

    def test_location_lat_out_of_range(self):
        with pytest.raises(ValidationError):
            _make(location_lat=91.0)

    def test_location_lng_bounds(self):
        e = _make(location_lng=-180.0)
        assert e.location_lng == -180.0

    def test_location_lng_out_of_range(self):
        with pytest.raises(ValidationError):
            _make(location_lng=181.0)

    def test_gcs_fields_optional(self):
        e = _make(gcp_bucket="my-bucket", gcp_object="path/to/file.jpg")
        assert e.gcp_bucket == "my-bucket"
        assert e.gcp_object == "path/to/file.jpg"


# ──────────────────────────────────────────────────────────────────────────────
# AI dispatch flags
# ──────────────────────────────────────────────────────────────────────────────

class TestAIDispatchFlags:
    @pytest.mark.parametrize("ct", ["site_photo", "drone_image"])
    def test_requires_vision_true(self, ct: str):
        e = _make(capture_type=ct)
        assert e.requires_vision is True

    @pytest.mark.parametrize("ct", ["voice_memo", "site_video", "document_upload",
                                     "form_submission", "iot_sensor"])
    def test_requires_vision_false(self, ct: str):
        e = _make(capture_type=ct)
        assert e.requires_vision is False

    def test_voice_memo_requires_speech(self):
        e = _make(capture_type="voice_memo")
        assert e.requires_speech is True

    @pytest.mark.parametrize("ct", ["site_photo", "document_upload", "form_submission"])
    def test_non_voice_does_not_require_speech(self, ct: str):
        e = _make(capture_type=ct)
        assert e.requires_speech is False

    @pytest.mark.parametrize("ct", [
        "document_upload", "surveyor_report", "inspection_report", "financial_document"
    ])
    def test_requires_ocr_true(self, ct: str):
        e = _make(capture_type=ct)
        assert e.requires_ocr is True

    @pytest.mark.parametrize("ct", ["site_photo", "voice_memo", "iot_sensor", "qr_scan"])
    def test_requires_ocr_false(self, ct: str):
        e = _make(capture_type=ct)
        assert e.requires_ocr is False


# ──────────────────────────────────────────────────────────────────────────────
# EvidenceUpdate
# ──────────────────────────────────────────────────────────────────────────────

class TestEvidenceUpdate:
    def test_empty_update_ok(self):
        u = EvidenceUpdate()
        assert u.model_dump(exclude_unset=True) == {}

    @pytest.mark.parametrize("status", [
        "draft", "submitted", "under_review", "approved", "rejected", "archived"
    ])
    def test_valid_statuses_accepted(self, status: str):
        u = EvidenceUpdate(status=status)
        assert u.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError, match="Invalid status"):
            EvidenceUpdate(status="pending")

    def test_metadata_patch_accepted(self):
        u = EvidenceUpdate(metadata={"key": "value"})
        assert u.metadata == {"key": "value"}

    def test_partial_update(self):
        u = EvidenceUpdate(status="approved", reliability_tier="primary")
        d = u.model_dump(exclude_unset=True)
        assert set(d.keys()) == {"status", "reliability_tier"}


# ──────────────────────────────────────────────────────────────────────────────
# EvidenceResponse
# ──────────────────────────────────────────────────────────────────────────────

class TestEvidenceResponse:
    def _base(self):
        now = datetime.now(timezone.utc)
        return {
            "id": uuid.uuid4(),
            "project_id": _PROJ,
            "tenant_id": uuid.uuid4(),
            "entity_type": "activity",
            "entity_id": _ENTITY,
            "capture_type": "site_photo",
            "status": "submitted",
            "captured_by": None,
            "captured_at": now,
            "file_ref": None,
            "description": None,
            "gcp_bucket": "my-bucket",
            "gcp_object": "photos/001.jpg",
            "reliability_tier": "secondary",
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }

    def test_from_dict(self):
        r = EvidenceResponse(**self._base())
        assert r.capture_type == "site_photo"

    def test_from_attributes_config(self):
        assert EvidenceResponse.model_config.get("from_attributes") is True

    def test_metadata_via_evidence_metadata_alias(self):
        # Router uses model_validate(orm_obj) where ORM attr is evidence_metadata
        mock_orm = MagicMock()
        for k, v in self._base().items():
            if k == "metadata":
                setattr(mock_orm, "evidence_metadata", v)
            else:
                setattr(mock_orm, k, v)
        r = EvidenceResponse.model_validate(mock_orm)
        assert r.metadata == {}

    def test_populate_by_name_allows_metadata_key(self):
        # Dict-based construction with field name (not alias) should work
        r = EvidenceResponse(**self._base())
        assert r.metadata == {}
