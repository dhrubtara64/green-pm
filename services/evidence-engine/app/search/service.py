"""Semantic evidence search — S4-02.

Cosine-similarity over stored embeddings in evidence_metadata["embedding"].
In production the caller passes a Vertex AI Matching Engine client; in tests
we use the in-process cosine implementation directly.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from ..evidence.service import list_evidence


@dataclass(frozen=True)
class SearchResult:
    evidence_id: uuid.UUID
    similarity_score: float


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Return cosine similarity ∈ [0, 1] between two vectors (same length)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(x ** 2 for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    raw = dot / (mag_a * mag_b)
    # Clamp to [0, 1] — negative cosine similarity treated as no match
    return max(0.0, min(1.0, raw))


async def semantic_search(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_embedding: Sequence[float],
    *,
    top_k: int = 10,
) -> list[SearchResult]:
    """Return up to top_k evidence records ranked by embedding similarity.

    Only evidences that have a stored embedding in evidence_metadata["embedding"]
    are considered. Evidences without embeddings are silently skipped.
    """
    if not query_embedding:
        return []

    evidences = await list_evidence(session, tenant_id, project_id, limit=1000)
    results: list[SearchResult] = []

    for ev in evidences:
        stored = ev.evidence_metadata.get("embedding")
        if not stored:
            continue
        score = _cosine_similarity(query_embedding, stored)
        results.append(SearchResult(evidence_id=ev.id, similarity_score=score))

    results.sort(key=lambda r: r.similarity_score, reverse=True)
    return results[:top_k]
