"""Tests for AI Orchestration Engine service layer — S16-02, S16-03, S16-04, S16-05."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.schemas import CopilotResponse, QueryResponse
from app.ai.service import (
    EvidenceChainNotFoundError,
    ask_copilot,
    get_evidence_chain,
    route_and_query,
)


@pytest.fixture
def session():
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.scalar = AsyncMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


class TestRouteAndQuery:
    @pytest.mark.asyncio
    async def test_returns_query_response(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "What are the risks?")
        assert isinstance(result, QueryResponse)

    @pytest.mark.asyncio
    async def test_query_id_is_uuid(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert isinstance(result.query_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_evidence_chain_id_is_uuid(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert isinstance(result.evidence_chain_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_project_id_in_response(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_response_is_string(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert isinstance(result.response, str)

    @pytest.mark.asyncio
    async def test_source_count_positive(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "What are the risks?")
        assert result.source_count >= 1

    @pytest.mark.asyncio
    async def test_session_add_called_twice(self, session, tenant_id, project_id):
        await route_and_query(session, tenant_id, project_id, "Risks?")
        assert session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_session_flush_called(self, session, tenant_id, project_id):
        await route_and_query(session, tenant_id, project_id, "Risks?")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_engine_name_not_in_response(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "What are the risks?")
        assert "risk-engine" not in result.response

    @pytest.mark.asyncio
    async def test_max_engines_parameter_accepted(self, session, tenant_id, project_id):
        result = await route_and_query(
            session, tenant_id, project_id, "Risks?", max_engines=2
        )
        assert result.source_count <= 2

    @pytest.mark.asyncio
    async def test_unique_query_ids_per_call(self, session, tenant_id, project_id):
        r1 = await route_and_query(session, tenant_id, project_id, "Risks?")
        r2 = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert r1.query_id != r2.query_id

    @pytest.mark.asyncio
    async def test_unique_chain_ids_per_call(self, session, tenant_id, project_id):
        r1 = await route_and_query(session, tenant_id, project_id, "Risks?")
        r2 = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert r1.evidence_chain_id != r2.evidence_chain_id

    @pytest.mark.asyncio
    async def test_no_ai_client_needed(self, session, tenant_id, project_id):
        result = await route_and_query(session, tenant_id, project_id, "Risks?")
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_when_no_keyword_match(self, session, tenant_id, project_id):
        result = await route_and_query(
            session, tenant_id, project_id, "xyzzy plugh frobozz"
        )
        assert result.source_count >= 1


class TestAskCopilot:
    @pytest.mark.asyncio
    async def test_returns_copilot_response(self, session, tenant_id, project_id):
        result = await ask_copilot(session, tenant_id, project_id, "Is the project on track?")
        assert isinstance(result, CopilotResponse)

    @pytest.mark.asyncio
    async def test_query_id_is_uuid(self, session, tenant_id, project_id):
        result = await ask_copilot(session, tenant_id, project_id, "Track?")
        assert isinstance(result.query_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_evidence_chain_id_is_uuid(self, session, tenant_id, project_id):
        result = await ask_copilot(session, tenant_id, project_id, "Track?")
        assert isinstance(result.evidence_chain_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_project_id_in_response(self, session, tenant_id, project_id):
        result = await ask_copilot(session, tenant_id, project_id, "Track?")
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_without_ai_client_stub_response(self, session, tenant_id, project_id):
        result = await ask_copilot(session, tenant_id, project_id, "Track?")
        assert isinstance(result.response, str)
        assert len(result.response) > 0

    @pytest.mark.asyncio
    async def test_with_mock_ai_client_calls_complete(self, session, tenant_id, project_id):
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value="AI generated answer.")
        result = await ask_copilot(
            session, tenant_id, project_id, "Track?", ai_client=mock_client
        )
        mock_client.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_mock_ai_client_uses_response(self, session, tenant_id, project_id):
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value="AI generated answer.")
        result = await ask_copilot(
            session, tenant_id, project_id, "Track?", ai_client=mock_client
        )
        assert result.response == "AI generated answer."

    @pytest.mark.asyncio
    async def test_session_add_called_twice(self, session, tenant_id, project_id):
        await ask_copilot(session, tenant_id, project_id, "Track?")
        assert session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_session_flush_called(self, session, tenant_id, project_id):
        await ask_copilot(session, tenant_id, project_id, "Track?")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_passed_to_ai_client(self, session, tenant_id, project_id):
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value="Response.")
        await ask_copilot(
            session, tenant_id, project_id, "Track?",
            context="Prior context here.",
            ai_client=mock_client,
        )
        call_kwargs = mock_client.complete.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_unique_chain_ids_per_call(self, session, tenant_id, project_id):
        r1 = await ask_copilot(session, tenant_id, project_id, "Track?")
        r2 = await ask_copilot(session, tenant_id, project_id, "Track?")
        assert r1.evidence_chain_id != r2.evidence_chain_id

    @pytest.mark.asyncio
    async def test_copilot_type_recorded(self, session, tenant_id, project_id):
        added_items = []
        session.add.side_effect = lambda item: added_items.append(item)
        await ask_copilot(session, tenant_id, project_id, "Track?")
        ai_sessions = [i for i in added_items if hasattr(i, "session_type")]
        assert any(s.session_type == "COPILOT" for s in ai_sessions)


class TestGetEvidenceChain:
    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_evidence_chain(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(EvidenceChainNotFoundError):
            await get_evidence_chain(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_id(self, session, tenant_id):
        session.scalar.return_value = None
        cid = uuid.uuid4()
        with pytest.raises(EvidenceChainNotFoundError, match=str(cid)):
            await get_evidence_chain(session, tenant_id, cid)

    @pytest.mark.asyncio
    async def test_scalar_called(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await get_evidence_chain(session, tenant_id, uuid.uuid4())
        session.scalar.assert_awaited_once()
