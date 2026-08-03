"""Unit tests for semantic evidence search — S4-02."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.search.service as _search_mod
from app.search.service import SearchResult, _cosine_similarity, semantic_search

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()


def _make_evidence(ev_id=None, embedding=None):
    m = MagicMock()
    m.id = ev_id or uuid.uuid4()
    m.evidence_metadata = {"embedding": embedding} if embedding is not None else {}
    return m


def _make_session(evidence_list=None):
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = evidence_list or []
    session.execute = AsyncMock(return_value=result_mock)
    return session


# ──────────────────────────────────────────────────────────────────────────────
# _cosine_similarity
# ──────────────────────────────────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 0.0, 0.0]
        assert _cosine_similarity(a, a) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_clamped_to_zero(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == 0.0  # negative clamped to 0

    def test_partial_similarity(self):
        a = [1.0, 1.0, 0.0]
        b = [1.0, 0.0, 0.0]
        result = _cosine_similarity(a, b)
        assert 0.6 < result < 0.8  # cos(45°) ≈ 0.707

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_different_lengths_returns_zero(self):
        a = [1.0, 2.0]
        b = [1.0, 2.0, 3.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_empty_vectors_returns_zero(self):
        assert _cosine_similarity([], []) == 0.0

    def test_result_in_zero_to_one(self):
        a = [0.3, 0.7, 0.1]
        b = [0.9, 0.1, 0.5]
        result = _cosine_similarity(a, b)
        assert 0.0 <= result <= 1.0


# ──────────────────────────────────────────────────────────────────────────────
# semantic_search
# ──────────────────────────────────────────────────────────────────────────────

class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_returns_empty_for_no_evidences(self):
        session = _make_session([])
        with patch_list_evidence([]):
            results = await semantic_search(session, _TENANT, _PROJECT, [1.0, 0.0, 0.0])
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_query(self):
        session = _make_session()
        with patch_list_evidence([]):
            results = await semantic_search(session, _TENANT, _PROJECT, [])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_evidences_without_embedding(self):
        ev = _make_evidence(embedding=None)
        with patch_list_evidence([ev]):
            results = await semantic_search(AsyncMock(), _TENANT, _PROJECT, [1.0, 0.0])
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_search_result_with_score(self):
        eid = uuid.uuid4()
        ev = _make_evidence(ev_id=eid, embedding=[1.0, 0.0, 0.0])
        with patch_list_evidence([ev]):
            results = await semantic_search(AsyncMock(), _TENANT, _PROJECT, [1.0, 0.0, 0.0])
        assert len(results) == 1
        assert results[0].evidence_id == eid
        assert results[0].similarity_score == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_results_sorted_by_similarity_desc(self):
        id1, id2, id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        evs = [
            _make_evidence(ev_id=id1, embedding=[1.0, 0.0]),   # cos=1.0 with [1,0]
            _make_evidence(ev_id=id2, embedding=[0.5, 0.5]),   # cos≈0.707
            _make_evidence(ev_id=id3, embedding=[0.0, 1.0]),   # cos=0.0
        ]
        with patch_list_evidence(evs):
            results = await semantic_search(AsyncMock(), _TENANT, _PROJECT, [1.0, 0.0])
        assert results[0].evidence_id == id1
        assert results[1].evidence_id == id2
        assert results[2].evidence_id == id3

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self):
        evs = [_make_evidence(embedding=[float(i), 0.0]) for i in range(1, 6)]
        with patch_list_evidence(evs):
            results = await semantic_search(AsyncMock(), _TENANT, _PROJECT, [1.0, 0.0], top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_result_is_frozen_dataclass(self):
        r = SearchResult(evidence_id=uuid.uuid4(), similarity_score=0.8)
        with pytest.raises((AttributeError, TypeError)):
            r.similarity_score = 0.9  # type: ignore[misc]


def patch_list_evidence(evs):
    """Context manager to patch list_evidence in the search service module."""
    from unittest.mock import patch
    return patch.object(_search_mod, "list_evidence", AsyncMock(return_value=evs))
