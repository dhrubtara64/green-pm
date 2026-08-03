"""Unit tests for AI client protocols — S3-02, S3-03, S3-04."""
from __future__ import annotations

import pytest

from app.ai_clients.vision import (
    GCPVisionClient,
    ImageClassification,
    StubVisionClient,
    VisionClient,
)
from app.ai_clients.speech import (
    GCPSpeechClient,
    StubSpeechClient,
    SpeechClient,
    TranscriptionResult,
    TRANSCRIPTION_COMPLETE,
    TRANSCRIPTION_FAILED,
    TRANSCRIPTION_IN_PROGRESS,
)
from app.ai_clients.ocr import (
    GCPOCRClient,
    OCRClient,
    OCRResult,
    StubOCRClient,
    _extract_structured_fields,
)


# ──────────────────────────────────────────────────────────────────────────────
# S3-02 — Vision API client
# ──────────────────────────────────────────────────────────────────────────────

class TestVisionClientProtocol:
    def test_stub_satisfies_protocol(self):
        client = StubVisionClient()
        assert isinstance(client, VisionClient)

    def test_gcp_satisfies_protocol(self):
        client = GCPVisionClient()
        assert isinstance(client, VisionClient)

    @pytest.mark.asyncio
    async def test_stub_returns_classification(self):
        client = StubVisionClient()
        result = await client.classify_image("gs://bucket/photo.jpg")
        assert isinstance(result, ImageClassification)

    @pytest.mark.asyncio
    async def test_stub_default_result_safe_search_passes(self):
        client = StubVisionClient()
        result = await client.classify_image("gs://bucket/photo.jpg")
        assert result.safe_search_passed is True

    @pytest.mark.asyncio
    async def test_stub_returns_objects_detected(self):
        client = StubVisionClient()
        result = await client.classify_image("gs://bucket/photo.jpg")
        assert len(result.objects_detected) > 0

    @pytest.mark.asyncio
    async def test_stub_custom_result_used(self):
        custom = ImageClassification(
            objects_detected=("crane",),
            dominant_labels=("machinery",),
            text_detected=(),
            safe_search_passed=True,
            confidence=0.5,
        )
        client = StubVisionClient(result=custom)
        result = await client.classify_image("gs://bucket/photo.jpg")
        assert result.dominant_labels == ("machinery",)

    @pytest.mark.asyncio
    async def test_stub_manual_review_result(self):
        custom = ImageClassification(
            requires_manual_review=True,
            error_message="API quota exceeded",
        )
        client = StubVisionClient(result=custom)
        result = await client.classify_image("gs://bucket/photo.jpg")
        assert result.requires_manual_review is True
        assert result.error_message == "API quota exceeded"

    @pytest.mark.asyncio
    async def test_gcp_client_gracefully_handles_no_library(self):
        # google-cloud-vision is not installed in this env — should not raise
        client = GCPVisionClient()
        result = await client.classify_image("gs://bucket/photo.jpg")
        assert isinstance(result, ImageClassification)
        assert result.requires_manual_review is True

    def test_image_classification_is_frozen(self):
        c = ImageClassification()
        with pytest.raises((AttributeError, TypeError)):
            c.confidence = 0.9  # type: ignore[misc]

    def test_image_classification_defaults(self):
        c = ImageClassification()
        assert c.objects_detected == ()
        assert c.safe_search_passed is True
        assert c.confidence == 0.0
        assert c.requires_manual_review is False


# ──────────────────────────────────────────────────────────────────────────────
# S3-03 — Speech-to-Text client
# ──────────────────────────────────────────────────────────────────────────────

class TestSpeechClientProtocol:
    def test_stub_satisfies_protocol(self):
        client = StubSpeechClient()
        assert isinstance(client, SpeechClient)

    def test_gcp_satisfies_protocol(self):
        client = GCPSpeechClient()
        assert isinstance(client, SpeechClient)

    @pytest.mark.asyncio
    async def test_stub_returns_transcription(self):
        client = StubSpeechClient()
        result = await client.transcribe_audio("gs://bucket/memo.wav")
        assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_stub_default_status_complete(self):
        client = StubSpeechClient()
        result = await client.transcribe_audio("gs://bucket/memo.wav")
        assert result.status == TRANSCRIPTION_COMPLETE

    @pytest.mark.asyncio
    async def test_stub_default_result_has_transcript(self):
        client = StubSpeechClient()
        result = await client.transcribe_audio("gs://bucket/memo.wav")
        assert len(result.transcript) > 0

    @pytest.mark.asyncio
    async def test_stub_custom_failed_result(self):
        custom = TranscriptionResult(
            transcript="",
            confidence=0.0,
            status=TRANSCRIPTION_FAILED,
            error_message="Audio format not supported",
        )
        client = StubSpeechClient(result=custom)
        result = await client.transcribe_audio("gs://bucket/memo.wav")
        assert result.status == TRANSCRIPTION_FAILED
        assert not result.succeeded

    @pytest.mark.asyncio
    async def test_stub_succeeded_property(self):
        client = StubSpeechClient()
        result = await client.transcribe_audio("gs://bucket/memo.wav")
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_gcp_client_gracefully_handles_no_library(self):
        client = GCPSpeechClient()
        result = await client.transcribe_audio("gs://bucket/memo.wav")
        assert result.status == TRANSCRIPTION_FAILED
        assert "not installed" in result.error_message

    def test_transcription_status_constants(self):
        assert TRANSCRIPTION_IN_PROGRESS == "transcribing"
        assert TRANSCRIPTION_COMPLETE == "complete"
        assert TRANSCRIPTION_FAILED == "failed"

    def test_transcription_result_is_frozen(self):
        r = TranscriptionResult(transcript="hello", confidence=0.9)
        with pytest.raises((AttributeError, TypeError)):
            r.transcript = "changed"  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# S3-04 — OCR client
# ──────────────────────────────────────────────────────────────────────────────

class TestOCRClientProtocol:
    def test_stub_satisfies_protocol(self):
        client = StubOCRClient()
        assert isinstance(client, OCRClient)

    def test_gcp_satisfies_protocol(self):
        client = GCPOCRClient()
        assert isinstance(client, OCRClient)

    @pytest.mark.asyncio
    async def test_stub_returns_ocr_result(self):
        client = StubOCRClient()
        result = await client.extract_text("gs://bucket/report.pdf")
        assert isinstance(result, OCRResult)

    @pytest.mark.asyncio
    async def test_stub_default_has_raw_text(self):
        client = StubOCRClient()
        result = await client.extract_text("gs://bucket/report.pdf")
        assert len(result.raw_text) > 0

    @pytest.mark.asyncio
    async def test_stub_default_has_structured_fields(self):
        client = StubOCRClient()
        result = await client.extract_text("gs://bucket/report.pdf")
        assert "document_number" in result.structured_fields

    @pytest.mark.asyncio
    async def test_stub_succeeded_when_text_present(self):
        client = StubOCRClient()
        result = await client.extract_text("gs://bucket/report.pdf")
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_stub_custom_failed_result(self):
        custom = OCRResult(
            raw_text="",
            requires_manual_review=True,
            error_message="File corrupt",
        )
        client = StubOCRClient(result=custom)
        result = await client.extract_text("gs://bucket/corrupt.pdf")
        assert result.requires_manual_review is True
        assert not result.succeeded

    @pytest.mark.asyncio
    async def test_gcp_client_gracefully_handles_no_library(self):
        client = GCPOCRClient()
        result = await client.extract_text("gs://bucket/report.pdf")
        assert result.requires_manual_review is True
        assert "not installed" in result.error_message

    def test_ocr_result_is_frozen(self):
        r = OCRResult(raw_text="text")
        with pytest.raises((AttributeError, TypeError)):
            r.raw_text = "changed"  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# Structured field extraction helper
# ──────────────────────────────────────────────────────────────────────────────

class TestExtractStructuredFields:
    def test_extracts_drawing_number(self):
        text = "Drawing DRG-2024-042 Rev B"
        fields = _extract_structured_fields(text)
        assert "document_number" in fields

    def test_extracts_revision(self):
        text = "REV. C approved on 15/07/2026"
        fields = _extract_structured_fields(text)
        assert "revision" in fields

    def test_extracts_progress_pct(self):
        text = "Activity completion: 75%"
        fields = _extract_structured_fields(text)
        assert "progress_pct" in fields
        assert "75" in fields["progress_pct"]

    def test_extracts_date(self):
        text = "Inspection date: 12/07/2026"
        fields = _extract_structured_fields(text)
        assert "date" in fields

    def test_empty_text_returns_empty_dict(self):
        fields = _extract_structured_fields("")
        assert fields == {}

    def test_no_patterns_returns_empty_dict(self):
        fields = _extract_structured_fields("random text without any recognisable patterns here")
        assert fields == {}

    def test_multiple_fields_extracted(self):
        text = "DOC-001 REV A 50% 01/01/2026"
        fields = _extract_structured_fields(text)
        assert len(fields) >= 3
