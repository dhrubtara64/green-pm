"""Tests for AI Orchestration Engine schemas — S16-02, S16-03, S16-04."""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.ai.schemas import (
    SUPPORTED_ENGINES,
    AIQuery,
    CopilotRequest,
    CopilotResponse,
    EvidenceChain,
    EvidenceChainResponse,
    QueryRequest,
    QueryResponse,
)


class TestSupportedEngines:
    def test_has_sixteen_engines(self):
        assert len(SUPPORTED_ENGINES) == 16

    def test_is_frozenset(self):
        assert isinstance(SUPPORTED_ENGINES, frozenset)

    def test_contains_risk_engine(self):
        assert "risk-engine" in SUPPORTED_ENGINES

    def test_contains_core_platform(self):
        assert "core-platform" in SUPPORTED_ENGINES


class TestAIQuery:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            query_text="What are the top risks this week?",
        )
        defaults.update(kwargs)
        return AIQuery(**defaults)

    def test_creates_successfully(self):
        q = self._make()
        assert "risks" in q.query_text

    def test_is_frozen(self):
        q = self._make()
        with pytest.raises((AttributeError, TypeError)):
            q.query_text = "changed"  # type: ignore[misc]

    def test_default_max_engines(self):
        q = self._make()
        assert q.max_engines == 5

    def test_custom_max_engines(self):
        q = self._make(max_engines=3)
        assert q.max_engines == 3

    def test_empty_query_text_raises(self):
        with pytest.raises(ValueError):
            self._make(query_text="   ")

    def test_max_engines_zero_raises(self):
        with pytest.raises(ValueError):
            self._make(max_engines=0)

    def test_max_engines_above_sixteen_raises(self):
        with pytest.raises(ValueError):
            self._make(max_engines=17)

    def test_max_engines_one_valid(self):
        q = self._make(max_engines=1)
        assert q.max_engines == 1

    def test_max_engines_sixteen_valid(self):
        q = self._make(max_engines=16)
        assert q.max_engines == 16

    def test_project_id_stored(self):
        pid = uuid.uuid4()
        q = self._make(project_id=pid)
        assert q.project_id == pid


class TestEvidenceChain:
    def _make(self, **kwargs):
        defaults = dict(
            chain_id=uuid.uuid4(),
            query_id=uuid.uuid4(),
            pig_node_ids=frozenset({uuid.uuid4()}),
            scores_used={"risk": 0.8},
            engines_consulted=frozenset({"risk-engine"}),
            created_at=datetime.now(timezone.utc),
        )
        defaults.update(kwargs)
        return EvidenceChain(**defaults)

    def test_creates_successfully(self):
        ec = self._make()
        assert isinstance(ec.chain_id, uuid.UUID)

    def test_is_frozen(self):
        ec = self._make()
        with pytest.raises((AttributeError, TypeError)):
            ec.chain_id = uuid.uuid4()  # type: ignore[misc]

    def test_pig_node_ids_stored(self):
        nids = frozenset({uuid.uuid4(), uuid.uuid4()})
        ec = self._make(pig_node_ids=nids)
        assert ec.pig_node_ids == nids

    def test_scores_used_stored(self):
        ec = self._make(scores_used={"forecast": 0.7})
        assert ec.scores_used["forecast"] == pytest.approx(0.7)

    def test_engines_consulted_stored(self):
        engines = frozenset({"risk-engine", "impact-engine"})
        ec = self._make(engines_consulted=engines)
        assert ec.engines_consulted == engines

    def test_created_at_stored(self):
        now = datetime.now(timezone.utc)
        ec = self._make(created_at=now)
        assert ec.created_at == now


class TestQueryRequest:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            query_text="What is the critical path status?",
        )
        defaults.update(kwargs)
        return QueryRequest(**defaults)

    def test_creates_successfully(self):
        req = self._make()
        assert req.query_text == "What is the critical path status?"

    def test_default_max_engines(self):
        req = self._make()
        assert req.max_engines == 5

    def test_empty_query_text_raises(self):
        with pytest.raises(ValidationError):
            self._make(query_text="  ")

    def test_max_engines_zero_raises(self):
        with pytest.raises(ValidationError):
            self._make(max_engines=0)

    def test_max_engines_seventeen_raises(self):
        with pytest.raises(ValidationError):
            self._make(max_engines=17)

    def test_max_engines_boundary_one(self):
        req = self._make(max_engines=1)
        assert req.max_engines == 1

    def test_max_engines_boundary_sixteen(self):
        req = self._make(max_engines=16)
        assert req.max_engines == 16


class TestCopilotRequest:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            query_text="Is the project on track?",
        )
        defaults.update(kwargs)
        return CopilotRequest(**defaults)

    def test_creates_successfully(self):
        req = self._make()
        assert "track" in req.query_text

    def test_context_defaults_none(self):
        req = self._make()
        assert req.context is None

    def test_context_accepted(self):
        req = self._make(context="Previous conversation context here.")
        assert req.context is not None

    def test_empty_query_text_raises(self):
        with pytest.raises(ValidationError):
            self._make(query_text="")


class TestQueryResponse:
    def test_creates_successfully(self):
        resp = QueryResponse(
            query_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            response="Here is the analysis.",
            evidence_chain_id=uuid.uuid4(),
            source_count=3,
        )
        assert resp.source_count == 3

    def test_from_attributes_config(self):
        assert QueryResponse.model_config.get("from_attributes") is True

    def test_evidence_chain_id_is_uuid(self):
        resp = QueryResponse(
            query_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            response="Analysis.",
            evidence_chain_id=uuid.uuid4(),
            source_count=1,
        )
        assert isinstance(resp.evidence_chain_id, uuid.UUID)


class TestCopilotResponse:
    def test_creates_successfully(self):
        resp = CopilotResponse(
            query_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            response="Ask Green PM response.",
            evidence_chain_id=uuid.uuid4(),
        )
        assert "Ask Green PM" in resp.response

    def test_from_attributes_config(self):
        assert CopilotResponse.model_config.get("from_attributes") is True


class TestEvidenceChainResponse:
    def test_creates_successfully(self):
        resp = EvidenceChainResponse(
            id=uuid.uuid4(),
            query_id=uuid.uuid4(),
        )
        assert resp.pig_node_ids == []

    def test_scores_used_defaults_empty(self):
        resp = EvidenceChainResponse(id=uuid.uuid4(), query_id=uuid.uuid4())
        assert resp.scores_used == {}

    def test_engines_consulted_defaults_empty(self):
        resp = EvidenceChainResponse(id=uuid.uuid4(), query_id=uuid.uuid4())
        assert resp.engines_consulted == []

    def test_created_at_defaults_none(self):
        resp = EvidenceChainResponse(id=uuid.uuid4(), query_id=uuid.uuid4())
        assert resp.created_at is None

    def test_from_attributes_config(self):
        assert EvidenceChainResponse.model_config.get("from_attributes") is True
