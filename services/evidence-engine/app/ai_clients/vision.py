"""Google Vision API client — S3-02.

Classifies site_photo and drone_image evidence via Google Cloud Vision.
Gracefully degrades to MANUAL_REVIEW on any API failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

_VISION_CAPTURE_TYPES = frozenset({"site_photo", "drone_image"})


@dataclass(frozen=True)
class ImageClassification:
    objects_detected: tuple[str, ...] = ()
    dominant_labels: tuple[str, ...] = ()
    text_detected: tuple[str, ...] = ()
    safe_search_passed: bool = True
    confidence: float = 0.0
    requires_manual_review: bool = False
    error_message: str = ""


@runtime_checkable
class VisionClient(Protocol):
    async def classify_image(self, gcs_uri: str) -> ImageClassification:
        """Classify an image at the given GCS URI."""
        ...


class GCPVisionClient:
    """Real implementation — uses google-cloud-vision library.

    Lazily imports the GCP library so the service starts without the SDK
    when running unit tests or in environments without credentials.
    """

    async def classify_image(self, gcs_uri: str) -> ImageClassification:
        try:
            from google.cloud import vision  # type: ignore[import]
        except ImportError:
            return ImageClassification(
                requires_manual_review=True,
                error_message="google-cloud-vision not installed",
            )
        try:
            client = vision.ImageAnnotatorClient()
            image = vision.Image(source=vision.ImageSource(image_uri=gcs_uri))

            label_response = client.label_detection(image=image)
            text_response = client.text_detection(image=image)
            safe_response = client.safe_search_detection(image=image)

            labels = [a.description for a in label_response.label_annotations]
            texts = [t.description for t in text_response.text_annotations[:5]]

            safe = safe_response.safe_search_annotation
            safe_passed = (
                safe.adult.value <= 2
                and safe.violence.value <= 2
                and safe.racy.value <= 2
            )
            confidence = (
                label_response.label_annotations[0].score
                if label_response.label_annotations
                else 0.0
            )
            return ImageClassification(
                objects_detected=tuple(labels[:10]),
                dominant_labels=tuple(labels[:3]),
                text_detected=tuple(texts),
                safe_search_passed=safe_passed,
                confidence=confidence,
            )
        except Exception as exc:
            return ImageClassification(
                requires_manual_review=True,
                error_message=str(exc)[:500],
            )


class StubVisionClient:
    """Deterministic test double."""

    def __init__(self, result: ImageClassification | None = None) -> None:
        self._result = result or ImageClassification(
            objects_detected=("scaffold", "concrete"),
            dominant_labels=("construction", "building"),
            text_detected=("DRG-001",),
            safe_search_passed=True,
            confidence=0.91,
        )

    async def classify_image(self, gcs_uri: str) -> ImageClassification:
        return self._result
