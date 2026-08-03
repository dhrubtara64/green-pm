"""Unit tests for Evidence service — S3-01 (service layer)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.evidence.service as _svc
from app.ai_clients.ocr import OCRResult, StubOCRClient
from app.ai_clients.speech import (
    StubSpeechClient,
    TranscriptionResult,
    TRANSCRIPTION_COMPLETE,
    TRANSCRIPTION_FAILED,
    TRANSCRIPTION_IN_PROGRESS,
)
from app.ai_clients.vision import ImageClassification, StubVisionClient
from app.evidence.schemas import EvidenceCreate, EvidenceUpdate
from app.evidence.service import (
    EvidenceNotFoundError,
    create_evidence,
    get_evidence,
    list_evidence,
    process_ocr,
    process_speech,
    process_vision,
    update_evidence,
)

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_USER = uuid.uuid4()
_ENTITY = uuid.uuid4()


def _make_create(**kwargs) -> EvidenceCreate:
    defaults = {
        "project_id": _PROJECT,
        "entity_type": "activity",
        "entity_id": _ENTITY,
        "capture_type": "site_photo",
        "gcp_bucket": "green-pm-evidence",
        "gcp_object": "photos/001.jpg",
    }
    defaults.update(kwargs)
    return EvidenceCreate(**defaults)


def _make_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_evidence(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "project_id": _PROJECT,
        "tenant_id": _TENANT,
        "entity_type": "activity",
        "entity_id": _ENTITY,
        "capture_type": "site_photo",
        "status": "submitted",
        "captured_by": _USER,
        "captured_at": datetime.now(timezone.utc),
        "file_ref": None,
        "description": None,
        "gcp_bucket": "green-pm-evidence",
        "gcp_object": "photos/001.jpg",
        "reliability_tier": "secondary",
        "evidence_metadata": {},
    }
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ──────────────────────────────────────────────────────────────────────────────
# create_evidence
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateEvidence:
    @pytest.mark.asyncio
    async def test_adds_evidence_to_session(self):
        session = _make_session()
        with patch.object(_svc, "write_outbox_event", new=AsyncMock()):
            await create_evidence(session, _TENANT, _USER, _make_create())
        assert session.add.called

    @pytest.mark.asyncio
    async def test_status_set_to_submitted(self):
        session = _make_session()
        added = {}

        def capture_add(obj):
            added["obj"] = obj

        session.add = capture_add
        with patch.object(_svc, "write_outbox_event", new=AsyncMock()):
            await create_evidence(session, _TENANT, _USER, _make_create())
        assert added["obj"].status == "submitted"

    @pytest.mark.asyncio
    async def test_outbox_event_written(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with patch.object(_svc, "write_outbox_event", new=mock_outbox):
            await create_evidence(session, _TENANT, _USER, _make_create())
        mock_outbox.assert_called_once()
        assert mock_outbox.call_args.kwargs["event_type"] == "EvidenceSubmitted"

    @pytest.mark.asyncio
    async def test_outbox_topic_is_evidence(self):
        session = _make_session()
        mock_outbox = AsyncMock()
        with patch.object(_svc, "write_outbox_event", new=mock_outbox):
            await create_evidence(session, _TENANT, _USER, _make_create())
        assert mock_outbox.call_args.kwargs["topic"] == "greenpm.evidence"

    @pytest.mark.asyncio
    async def test_flush_called(self):
        session = _make_session()
        with patch.object(_svc, "write_outbox_event", new=AsyncMock()):
            await create_evidence(session, _TENANT, _USER, _make_create())
        assert session.flush.called


# ──────────────────────────────────────────────────────────────────────────────
# get_evidence
# ──────────────────────────────────────────────────────────────────────────────

class TestGetEvidence:
    @pytest.mark.asyncio
    async def test_returns_evidence_when_found(self):
        session = _make_session()
        ev = _make_evidence()
        session.scalar = AsyncMock(return_value=ev)
        result = await get_evidence(session, _TENANT, ev.id)
        assert result is ev

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        with pytest.raises(EvidenceNotFoundError):
            await get_evidence(session, _TENANT, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_not_found_error_contains_id(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        eid = uuid.uuid4()
        with pytest.raises(EvidenceNotFoundError, match=str(eid)):
            await get_evidence(session, _TENANT, eid)


# ──────────────────────────────────────────────────────────────────────────────
# list_evidence
# ──────────────────────────────────────────────────────────────────────────────

class TestListEvidence:
    @pytest.mark.asyncio
    async def test_returns_sequence(self):
        session = _make_session()
        items = [_make_evidence() for _ in range(3)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = items
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_evidence(session, _TENANT, _PROJECT)
        assert list(result) == items

    @pytest.mark.asyncio
    async def test_empty_list(self):
        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_evidence(session, _TENANT, _PROJECT)
        assert list(result) == []


# ──────────────────────────────────────────────────────────────────────────────
# update_evidence
# ──────────────────────────────────────────────────────────────────────────────

class TestUpdateEvidence:
    @pytest.mark.asyncio
    async def test_updates_status(self):
        session = _make_session()
        ev = _make_evidence(status="submitted")
        session.scalar = AsyncMock(return_value=ev)
        await update_evidence(session, _TENANT, ev.id, EvidenceUpdate(status="approved"))
        assert ev.status == "approved"

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        session = _make_session()
        session.scalar = AsyncMock(return_value=None)
        with pytest.raises(EvidenceNotFoundError):
            await update_evidence(session, _TENANT, uuid.uuid4(), EvidenceUpdate())

    @pytest.mark.asyncio
    async def test_metadata_merged_not_replaced(self):
        session = _make_session()
        ev = _make_evidence(evidence_metadata={"existing": "value"})
        session.scalar = AsyncMock(return_value=ev)
        await update_evidence(
            session, _TENANT, ev.id,
            EvidenceUpdate(metadata={"new_key": "new_value"})
        )
        assert ev.evidence_metadata.get("existing") == "value"
        assert ev.evidence_metadata.get("new_key") == "new_value"


# ──────────────────────────────────────────────────────────────────────────────
# process_vision (S3-02)
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessVision:
    @pytest.mark.asyncio
    async def test_metadata_updated_with_vision_result(self):
        session = _make_session()
        ev = _make_evidence(
            capture_type="site_photo",
            gcp_bucket="bucket",
            gcp_object="photo.jpg",
            evidence_metadata={},
        )
        client = StubVisionClient()
        await process_vision(session, ev, client)
        assert "vision" in ev.evidence_metadata

    @pytest.mark.asyncio
    async def test_safe_search_result_stored(self):
        session = _make_session()
        ev = _make_evidence(capture_type="drone_image", evidence_metadata={})
        client = StubVisionClient()
        await process_vision(session, ev, client)
        assert "safe_search_passed" in ev.evidence_metadata["vision"]

    @pytest.mark.asyncio
    async def test_manual_review_sets_status(self):
        session = _make_session()
        ev = _make_evidence(capture_type="site_photo", status="submitted", evidence_metadata={})
        bad = ImageClassification(requires_manual_review=True, error_message="quota")
        client = StubVisionClient(result=bad)
        await process_vision(session, ev, client)
        assert ev.status == "under_review"

    @pytest.mark.asyncio
    async def test_flush_called_after_vision(self):
        session = _make_session()
        ev = _make_evidence(capture_type="site_photo", evidence_metadata={})
        await process_vision(session, ev, StubVisionClient())
        assert session.flush.called


# ──────────────────────────────────────────────────────────────────────────────
# process_speech (S3-03)
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessSpeech:
    @pytest.mark.asyncio
    async def test_status_transitions_pending_to_complete(self):
        session = _make_session()
        states = []
        orig_flush = session.flush

        async def capture_flush():
            states.append(ev.evidence_metadata.get("transcription_status"))

        session.flush = capture_flush
        ev = _make_evidence(capture_type="voice_memo", evidence_metadata={})
        await process_speech(session, ev, StubSpeechClient())
        assert TRANSCRIPTION_IN_PROGRESS in states
        assert ev.evidence_metadata["transcription_status"] == TRANSCRIPTION_COMPLETE

    @pytest.mark.asyncio
    async def test_transcript_stored_in_metadata(self):
        session = _make_session()
        ev = _make_evidence(capture_type="voice_memo", evidence_metadata={})
        await process_speech(session, ev, StubSpeechClient())
        assert "transcript" in ev.evidence_metadata
        assert len(ev.evidence_metadata["transcript"]) > 0

    @pytest.mark.asyncio
    async def test_failed_transcription_stored(self):
        session = _make_session()
        ev = _make_evidence(capture_type="voice_memo", evidence_metadata={})
        bad = TranscriptionResult(
            transcript="", confidence=0.0,
            status=TRANSCRIPTION_FAILED, error_message="bad audio",
        )
        await process_speech(session, ev, StubSpeechClient(result=bad))
        assert ev.evidence_metadata["transcription_status"] == TRANSCRIPTION_FAILED
        assert "transcription_error" in ev.evidence_metadata

    @pytest.mark.asyncio
    async def test_word_count_stored(self):
        session = _make_session()
        ev = _make_evidence(capture_type="voice_memo", evidence_metadata={})
        await process_speech(session, ev, StubSpeechClient())
        assert "word_count" in ev.evidence_metadata


# ──────────────────────────────────────────────────────────────────────────────
# process_ocr (S3-04)
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessOCR:
    @pytest.mark.asyncio
    async def test_raw_text_stored(self):
        session = _make_session()
        ev = _make_evidence(capture_type="document_upload", evidence_metadata={})
        await process_ocr(session, ev, StubOCRClient())
        assert "ocr_raw_text" in ev.evidence_metadata
        assert len(ev.evidence_metadata["ocr_raw_text"]) > 0

    @pytest.mark.asyncio
    async def test_structured_fields_stored(self):
        session = _make_session()
        ev = _make_evidence(capture_type="inspection_report", evidence_metadata={})
        await process_ocr(session, ev, StubOCRClient())
        assert "ocr_fields" in ev.evidence_metadata
        assert isinstance(ev.evidence_metadata["ocr_fields"], dict)

    @pytest.mark.asyncio
    async def test_failed_ocr_sets_manual_review(self):
        session = _make_session()
        ev = _make_evidence(capture_type="surveyor_report", status="submitted", evidence_metadata={})
        bad = OCRResult(raw_text="", requires_manual_review=True, error_message="corrupt file")
        await process_ocr(session, ev, StubOCRClient(result=bad))
        assert ev.status == "under_review"
        assert "ocr_error" in ev.evidence_metadata

    @pytest.mark.asyncio
    async def test_page_count_stored(self):
        session = _make_session()
        ev = _make_evidence(capture_type="financial_document", evidence_metadata={})
        await process_ocr(session, ev, StubOCRClient())
        assert "ocr_page_count" in ev.evidence_metadata
