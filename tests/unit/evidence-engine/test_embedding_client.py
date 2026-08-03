"""Unit tests for Vertex AI Embedding client — S4-02."""
from __future__ import annotations

import pytest

from app.ai_clients.embedding import (
    EmbeddingClient,
    EmbeddingResult,
    GCPVertexEmbeddingClient,
    StubEmbeddingClient,
)


# ──────────────────────────────────────────────────────────────────────────────
# EmbeddingResult
# ──────────────────────────────────────────────────────────────────────────────

class TestEmbeddingResult:
    def test_succeeded_when_embedding_present(self):
        r = EmbeddingResult(embedding=(0.1, 0.2, 0.3), model="stub")
        assert r.succeeded is True

    def test_failed_when_error_message_set(self):
        r = EmbeddingResult(embedding=(0.1,), model="stub", error_message="quota exceeded")
        assert r.succeeded is False

    def test_failed_when_embedding_empty(self):
        r = EmbeddingResult(embedding=(), model="stub")
        assert r.succeeded is False

    def test_dimensions_count(self):
        r = EmbeddingResult(embedding=(1.0, 2.0, 3.0, 4.0))
        assert r.dimensions == 4

    def test_dimensions_zero_for_empty(self):
        r = EmbeddingResult()
        assert r.dimensions == 0

    def test_default_values(self):
        r = EmbeddingResult()
        assert r.embedding == ()
        assert r.model == ""
        assert r.error_message == ""

    def test_frozen_dataclass(self):
        r = EmbeddingResult(embedding=(1.0,))
        with pytest.raises((AttributeError, TypeError)):
            r.model = "changed"  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# StubEmbeddingClient
# ──────────────────────────────────────────────────────────────────────────────

class TestStubEmbeddingClient:
    @pytest.mark.asyncio
    async def test_returns_embedding_result(self):
        client = StubEmbeddingClient()
        result = await client.generate_embedding("activity site photo")
        assert isinstance(result, EmbeddingResult)

    @pytest.mark.asyncio
    async def test_embedding_has_correct_dimension(self):
        client = StubEmbeddingClient()
        result = await client.generate_embedding("test text")
        assert result.dimensions == StubEmbeddingClient._DIM

    @pytest.mark.asyncio
    async def test_stub_model_label(self):
        client = StubEmbeddingClient()
        result = await client.generate_embedding("anything")
        assert result.model == "stub"

    @pytest.mark.asyncio
    async def test_deterministic_same_text(self):
        client = StubEmbeddingClient()
        r1 = await client.generate_embedding("same text")
        r2 = await client.generate_embedding("same text")
        assert r1.embedding == r2.embedding

    @pytest.mark.asyncio
    async def test_different_texts_produce_different_embeddings(self):
        client = StubEmbeddingClient()
        r1 = await client.generate_embedding("alpha text here")
        r2 = await client.generate_embedding("beta text here different")
        assert r1.embedding != r2.embedding

    @pytest.mark.asyncio
    async def test_injectable_result(self):
        fixed = EmbeddingResult(embedding=(0.5, 0.5, 0.5, 0.5), model="injected")
        client = StubEmbeddingClient(result=fixed)
        result = await client.generate_embedding("any text")
        assert result is fixed

    @pytest.mark.asyncio
    async def test_succeeded_true(self):
        client = StubEmbeddingClient()
        result = await client.generate_embedding("test")
        assert result.succeeded is True

    @pytest.mark.asyncio
    async def test_embedding_values_in_range(self):
        client = StubEmbeddingClient()
        result = await client.generate_embedding("range check")
        for v in result.embedding:
            assert 0.0 <= v <= 1.0


# ──────────────────────────────────────────────────────────────────────────────
# GCPVertexEmbeddingClient — graceful degradation
# ──────────────────────────────────────────────────────────────────────────────

class TestGCPVertexEmbeddingClient:
    @pytest.mark.asyncio
    async def test_import_error_returns_error_result(self):
        client = GCPVertexEmbeddingClient()
        result = await client.generate_embedding("test")
        # In CI without GCP libs installed, should return error result (not raise)
        assert isinstance(result, EmbeddingResult)
        if not result.succeeded:
            assert result.error_message != ""

    def test_satisfies_protocol(self):
        client = StubEmbeddingClient()
        assert isinstance(client, EmbeddingClient)

    def test_gcp_client_has_generate_embedding(self):
        import inspect
        assert hasattr(GCPVertexEmbeddingClient, "generate_embedding")
        assert inspect.iscoroutinefunction(GCPVertexEmbeddingClient.generate_embedding)
