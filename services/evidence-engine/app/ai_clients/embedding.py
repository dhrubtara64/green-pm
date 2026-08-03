"""Vertex AI Embedding client — S4-02.

Protocol + GCP implementation (lazy import) + Stub for tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class EmbeddingResult:
    """Result of a text embedding call."""

    embedding: tuple[float, ...] = field(default_factory=tuple)
    model: str = ""
    error_message: str = ""

    @property
    def succeeded(self) -> bool:
        return bool(self.embedding) and not self.error_message

    @property
    def dimensions(self) -> int:
        return len(self.embedding)


@runtime_checkable
class EmbeddingClient(Protocol):
    async def generate_embedding(self, text: str) -> EmbeddingResult: ...


class GCPVertexEmbeddingClient:
    """Vertex AI text-embedding-004 client with lazy GCP import."""

    _MODEL = "text-embedding-004"

    def __init__(self, project: str = "", location: str = "asia-south1") -> None:
        self._project = project
        self._location = location

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        try:
            from vertexai.language_models import TextEmbeddingModel  # type: ignore[import]

            model = TextEmbeddingModel.from_pretrained(self._MODEL)
            embeddings = model.get_embeddings([text])
            vec = tuple(float(v) for v in embeddings[0].values)
            return EmbeddingResult(embedding=vec, model=self._MODEL)
        except ImportError:
            return EmbeddingResult(
                error_message="vertexai package not installed — pip install google-cloud-aiplatform"
            )
        except Exception as exc:
            return EmbeddingResult(error_message=str(exc))


class StubEmbeddingClient:
    """Deterministic test double — 4-dim unit vector derived from text hash."""

    _DIM = 4

    def __init__(self, result: Optional[EmbeddingResult] = None) -> None:
        self._result = result

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        if self._result is not None:
            return self._result
        h = abs(hash(text)) % 1000
        vec = tuple(float((h + i) % 100) / 100.0 for i in range(self._DIM))
        return EmbeddingResult(embedding=vec, model="stub")
