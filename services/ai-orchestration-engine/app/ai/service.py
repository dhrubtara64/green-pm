"""AI Orchestration Engine service layer — S16-02, S16-03, S16-04, S16-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.ai.model import AISession, EvidenceChainRecord
from app.ai.router import route_query, synthesize_responses
from app.ai.schemas import CopilotResponse, QueryResponse


class EvidenceChainNotFoundError(Exception):
    pass


async def route_and_query(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_text: str,
    max_engines: int = 5,
) -> QueryResponse:
    """Route NL query to matching engines and return a synthesized response — S16-02.

    Engine names are never surfaced in the QueryResponse.
    """
    query_id = uuid.uuid4()
    chain_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    engines = route_query(query_text, max_engines=max_engines)
    engine_responses = {e: f"Project intelligence analysis for: {query_text}" for e in engines}
    response_text = synthesize_responses(engine_responses)

    chain_record = EvidenceChainRecord(
        id=chain_id,
        tenant_id=tenant_id,
        query_id=query_id,
        pig_node_ids=[],
        scores_used={},
        engines_consulted=engines,
        created_at=now,
    )
    session.add(chain_record)

    ai_session = AISession(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        query_id=query_id,
        query_text=query_text,
        response_text=response_text,
        evidence_chain_id=chain_id,
        engines_consulted=engines,
        session_type="QUERY",
        created_at=now,
    )
    session.add(ai_session)
    await session.flush()

    return QueryResponse(
        query_id=query_id,
        project_id=project_id,
        response=response_text,
        evidence_chain_id=chain_id,
        source_count=len(engines),
    )


async def ask_copilot(
    session,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_text: str,
    context: Optional[str] = None,
    ai_client=None,
) -> CopilotResponse:
    """Call Ask Green PM copilot and store evidence chain — S16-03.

    ai_client is dependency-injected so unit tests can substitute a mock
    without making real Claude API calls.
    """
    query_id = uuid.uuid4()
    chain_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    engines = route_query(query_text, max_engines=5)

    if ai_client is not None:
        enriched_prompt = f"Project context query: {query_text}"
        response_text = await ai_client.complete(enriched_prompt, context=context)
    else:
        response_text = f"Ask Green PM: {query_text}"

    chain_record = EvidenceChainRecord(
        id=chain_id,
        tenant_id=tenant_id,
        query_id=query_id,
        pig_node_ids=[],
        scores_used={},
        engines_consulted=engines,
        created_at=now,
    )
    session.add(chain_record)

    ai_session = AISession(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        query_id=query_id,
        query_text=query_text,
        response_text=response_text,
        evidence_chain_id=chain_id,
        engines_consulted=engines,
        session_type="COPILOT",
        created_at=now,
    )
    session.add(ai_session)
    await session.flush()

    return CopilotResponse(
        query_id=query_id,
        project_id=project_id,
        response=response_text,
        evidence_chain_id=chain_id,
    )


async def get_evidence_chain(
    session,
    tenant_id: uuid.UUID,
    chain_id: uuid.UUID,
) -> EvidenceChainRecord:
    """Retrieve an evidence chain by id — S16-04."""
    stmt = select(EvidenceChainRecord).where(
        EvidenceChainRecord.tenant_id == tenant_id,
        EvidenceChainRecord.id == chain_id,
    )
    record = await session.scalar(stmt)
    if record is None:
        raise EvidenceChainNotFoundError(f"EvidenceChain {chain_id} not found")
    return record
