"""Cloud Speech-to-Text client — S3-03.

Transcribes voice_memo evidence asynchronously.
Status transitions tracked in evidence.metadata["transcription_status"]:
  pending → transcribing → complete | failed
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

TRANSCRIPTION_PENDING = "pending"
TRANSCRIPTION_IN_PROGRESS = "transcribing"
TRANSCRIPTION_COMPLETE = "complete"
TRANSCRIPTION_FAILED = "failed"


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str
    confidence: float
    language_code: str = "en-US"
    word_count: int = 0
    status: str = TRANSCRIPTION_COMPLETE
    error_message: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == TRANSCRIPTION_COMPLETE and not self.error_message


@runtime_checkable
class SpeechClient(Protocol):
    async def transcribe_audio(self, gcs_uri: str) -> TranscriptionResult:
        """Transcribe audio at the given GCS URI."""
        ...


class GCPSpeechClient:
    """Real implementation — uses google-cloud-speech library."""

    def __init__(self, language_code: str = "en-US") -> None:
        self._language_code = language_code

    async def transcribe_audio(self, gcs_uri: str) -> TranscriptionResult:
        try:
            from google.cloud import speech  # type: ignore[import]
        except ImportError:
            return TranscriptionResult(
                transcript="",
                confidence=0.0,
                status=TRANSCRIPTION_FAILED,
                error_message="google-cloud-speech not installed",
            )
        try:
            client = speech.SpeechClient()
            audio = speech.RecognitionAudio(uri=gcs_uri)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code=self._language_code,
                model="video",
                use_enhanced=True,
                enable_automatic_punctuation=True,
            )
            response = client.recognize(config=config, audio=audio)

            if not response.results:
                return TranscriptionResult(
                    transcript="",
                    confidence=0.0,
                    status=TRANSCRIPTION_COMPLETE,
                )
            best = response.results[0].alternatives[0]
            words = best.transcript.split()
            return TranscriptionResult(
                transcript=best.transcript,
                confidence=best.confidence,
                language_code=self._language_code,
                word_count=len(words),
                status=TRANSCRIPTION_COMPLETE,
            )
        except Exception as exc:
            return TranscriptionResult(
                transcript="",
                confidence=0.0,
                status=TRANSCRIPTION_FAILED,
                error_message=str(exc)[:500],
            )


class StubSpeechClient:
    """Deterministic test double."""

    def __init__(self, result: TranscriptionResult | None = None) -> None:
        self._result = result or TranscriptionResult(
            transcript="Pile cap at grid C3 is 85 percent complete, rebar placed.",
            confidence=0.94,
            language_code="en-US",
            word_count=12,
            status=TRANSCRIPTION_COMPLETE,
        )

    async def transcribe_audio(self, gcs_uri: str) -> TranscriptionResult:
        return self._result
