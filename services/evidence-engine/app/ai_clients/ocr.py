"""Cloud Vision OCR client — S3-04.

Extracts text and structured fields from document_upload, surveyor_report,
inspection_report, and financial_document evidence.
Raw OCR text is stored in evidence.metadata["ocr_raw_text"].
Structured fields (where recognisable) go into metadata["ocr_fields"].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class OCRResult:
    raw_text: str
    structured_fields: dict[str, Any] = field(default_factory=dict)
    page_count: int = 1
    confidence: float = 0.0
    requires_manual_review: bool = False
    error_message: str = ""

    @property
    def succeeded(self) -> bool:
        return bool(self.raw_text) and not self.error_message


@runtime_checkable
class OCRClient(Protocol):
    async def extract_text(self, gcs_uri: str) -> OCRResult:
        """Extract text (and structured fields where possible) from a document."""
        ...


# Patterns we attempt to extract as structured fields from construction docs
_FIELD_PATTERNS: list[tuple[str, str]] = [
    ("document_number", r"(?:DRG|DOC|DWG)[- ]?[A-Z0-9]{3,20}"),
    ("revision",        r"REV\.?\s*([A-Z0-9]{1,4})"),
    ("progress_pct",    r"(\d{1,3}(?:\.\d{1,2})?)\s*%"),
    ("date",            r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}"),
]


def _extract_structured_fields(text: str) -> dict[str, Any]:
    """Best-effort structured field extraction using regex patterns."""
    import re
    fields: dict[str, Any] = {}
    for field_name, pattern in _FIELD_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            fields[field_name] = m.group(0).strip()
    return fields


class GCPOCRClient:
    """Real implementation — uses google-cloud-vision Document Text Detection."""

    async def extract_text(self, gcs_uri: str) -> OCRResult:
        try:
            from google.cloud import vision  # type: ignore[import]
        except ImportError:
            return OCRResult(
                raw_text="",
                requires_manual_review=True,
                error_message="google-cloud-vision not installed",
            )
        try:
            client = vision.ImageAnnotatorClient()
            image = vision.Image(source=vision.ImageSource(image_uri=gcs_uri))
            response = client.document_text_detection(image=image)

            if response.error.message:
                return OCRResult(
                    raw_text="",
                    requires_manual_review=True,
                    error_message=response.error.message[:500],
                )

            full_text = response.full_text_annotation.text
            pages = response.full_text_annotation.pages
            confidence = (
                pages[0].confidence if pages and hasattr(pages[0], "confidence") else 0.0
            )
            structured = _extract_structured_fields(full_text)
            return OCRResult(
                raw_text=full_text,
                structured_fields=structured,
                page_count=len(pages) or 1,
                confidence=confidence,
            )
        except Exception as exc:
            return OCRResult(
                raw_text="",
                requires_manual_review=True,
                error_message=str(exc)[:500],
            )


class StubOCRClient:
    """Deterministic test double."""

    def __init__(self, result: OCRResult | None = None) -> None:
        self._result = result or OCRResult(
            raw_text="Drawing DRG-2024-042 REV B\nProgress: 75%\nDate: 15/07/2026",
            structured_fields={
                "document_number": "DRG-2024-042",
                "revision": "REV B",
                "progress_pct": "75%",
                "date": "15/07/2026",
            },
            page_count=1,
            confidence=0.97,
        )

    async def extract_text(self, gcs_uri: str) -> OCRResult:
        return self._result
