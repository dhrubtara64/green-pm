"""Evidence service — CRUD + AI dispatch + score computation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.outbox.writer import write_outbox_event

from ..ai_clients.embedding import EmbeddingClient
from ..ai_clients.ocr import OCRClient
from ..ai_clients.speech import SpeechClient, TRANSCRIPTION_IN_PROGRESS, TRANSCRIPTION_COMPLETE, TRANSCRIPTION_FAILED
from ..ai_clients.vision import VisionClient
from ..pig.edge_writer import sync_evidence_node
from ..scoring.formula import ComputedScore, EvidenceItem, compute_evidence_score
from .model import Evidence, EvidenceScore
from .schemas import EvidenceCreate, EvidenceUpdate

_EVIDENCE_TOPIC = "greenpm.evidence"


class EvidenceNotFoundError(Exception):
    def __init__(self, evidence_id: uuid.UUID) -> None:
        super().__init__(f"Evidence {evidence_id} not found")


async def create_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    captured_by: uuid.UUID,
    data: EvidenceCreate,
) -> Evidence:
    """Ingest one evidence record within the caller's transaction.

    Does NOT commit — caller owns the transaction boundary.
    """
    evidence = Evidence(
        id=uuid.uuid4(),
        project_id=data.project_id,
        tenant_id=tenant_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        capture_type=data.capture_type,
        status="submitted",
        captured_by=captured_by,
        captured_at=data.captured_at,
        file_ref=data.file_ref,
        description=data.description,
        gcp_bucket=data.gcp_bucket,
        gcp_object=data.gcp_object,
        reliability_tier=data.reliability_tier or "secondary",
        evidence_metadata=dict(data.metadata),
    )
    session.add(evidence)
    await session.flush()

    await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic=_EVIDENCE_TOPIC,
        event_type="EvidenceSubmitted",
        payload={
            "evidence_id": str(evidence.id),
            "project_id": str(data.project_id),
            "entity_type": data.entity_type,
            "entity_id": str(data.entity_id),
            "capture_type": data.capture_type,
        },
    )

    # Register evidence as a PIG node in the same transaction — S4-03
    await sync_evidence_node(session, evidence)

    return evidence


async def generate_and_store_embedding(
    session: AsyncSession,
    evidence: Evidence,
    client: EmbeddingClient,
) -> None:
    """Generate a text embedding for the evidence and store it in evidence_metadata.

    Called after ingestion (S4-02). Does NOT commit — caller owns transaction.
    """
    text_parts = [
        evidence.entity_type,
        evidence.capture_type,
        evidence.description or "",
    ]
    text = " ".join(p for p in text_parts if p).strip()
    result = await client.generate_embedding(text)
    if result.succeeded:
        evidence.evidence_metadata = {
            **evidence.evidence_metadata,
            "embedding": list(result.embedding),
            "embedding_model": result.model,
        }
        await session.flush()


async def get_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> Evidence:
    ev = await session.scalar(
        select(Evidence).where(
            and_(Evidence.id == evidence_id, Evidence.tenant_id == tenant_id)
        )
    )
    if ev is None:
        raise EvidenceNotFoundError(evidence_id)
    return ev


async def list_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    capture_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[Evidence]:
    q = (
        select(Evidence)
        .where(and_(Evidence.project_id == project_id, Evidence.tenant_id == tenant_id))
        .order_by(Evidence.captured_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if entity_type is not None:
        q = q.where(Evidence.entity_type == entity_type)
    if entity_id is not None:
        q = q.where(Evidence.entity_id == entity_id)
    if capture_type is not None:
        q = q.where(Evidence.capture_type == capture_type)
    if status is not None:
        q = q.where(Evidence.status == status)
    result = await session.execute(q)
    return result.scalars().all()


async def update_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
    data: EvidenceUpdate,
) -> Evidence:
    ev = await get_evidence(session, tenant_id, evidence_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata" and value is not None:
            ev.evidence_metadata = {**ev.evidence_metadata, **value}
        else:
            setattr(ev, field, value)
    await session.flush()
    return ev


# ── AI processing ─────────────────────────────────────────────────────────────

async def process_vision(
    session: AsyncSession,
    evidence: Evidence,
    client: VisionClient,
) -> None:
    """Classify a site_photo or drone_image; update metadata in-place."""
    gcs_uri = f"gs://{evidence.gcp_bucket}/{evidence.gcp_object}" if evidence.gcp_object else ""
    result = await client.classify_image(gcs_uri)
    evidence.evidence_metadata = {
        **evidence.evidence_metadata,
        "vision": {
            "objects_detected": list(result.objects_detected),
            "dominant_labels": list(result.dominant_labels),
            "text_detected": list(result.text_detected),
            "safe_search_passed": result.safe_search_passed,
            "confidence": result.confidence,
        },
    }
    if result.requires_manual_review:
        evidence.status = "under_review"
        evidence.evidence_metadata = {**evidence.evidence_metadata, "vision_error": result.error_message}
    await session.flush()


async def process_speech(
    session: AsyncSession,
    evidence: Evidence,
    client: SpeechClient,
) -> None:
    """Transcribe a voice_memo; transition through PENDING → TRANSCRIBING → COMPLETE."""
    gcs_uri = f"gs://{evidence.gcp_bucket}/{evidence.gcp_object}" if evidence.gcp_object else ""

    # Mark as in-progress
    evidence.evidence_metadata = {**evidence.evidence_metadata, "transcription_status": TRANSCRIPTION_IN_PROGRESS}
    await session.flush()

    result = await client.transcribe_audio(gcs_uri)

    evidence.evidence_metadata = {
        **evidence.evidence_metadata,
        "transcription_status": result.status,
        "transcript": result.transcript,
        "transcription_confidence": result.confidence,
        "word_count": result.word_count,
    }
    if not result.succeeded:
        evidence.evidence_metadata = {**evidence.evidence_metadata, "transcription_error": result.error_message}
    await session.flush()


async def process_ocr(
    session: AsyncSession,
    evidence: Evidence,
    client: OCRClient,
) -> None:
    """Extract text from a document; store raw + structured fields in metadata."""
    gcs_uri = f"gs://{evidence.gcp_bucket}/{evidence.gcp_object}" if evidence.gcp_object else ""
    result = await client.extract_text(gcs_uri)
    evidence.evidence_metadata = {
        **evidence.evidence_metadata,
        "ocr_raw_text": result.raw_text,
        "ocr_fields": result.structured_fields,
        "ocr_page_count": result.page_count,
        "ocr_confidence": result.confidence,
    }
    if result.requires_manual_review:
        evidence.status = "under_review"
        evidence.evidence_metadata = {**evidence.evidence_metadata, "ocr_error": result.error_message}
    await session.flush()


# ── Evidence Score computation ─────────────────────────────────────────────────

async def compute_and_store_score(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    *,
    corroboration_ratio: float = 1.0,
) -> ComputedScore:
    """Recompute and upsert Evidence Score for (project, entity_type, entity_id)."""
    rows = await list_evidence(
        session, tenant_id, project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        status="submitted",
        limit=1000,
    )
    now = datetime.now(timezone.utc)
    items = [
        EvidenceItem(
            captured_at=ev.captured_at,
            capture_type=ev.capture_type,
            reliability_tier=ev.reliability_tier,
        )
        for ev in rows
    ]
    score = compute_evidence_score(items, now=now, corroboration_ratio=corroboration_ratio)

    # Upsert — ON CONFLICT (project_id, entity_type, entity_id) DO UPDATE
    stmt = pg_insert(EvidenceScore).values(
        id=uuid.uuid4(),
        project_id=project_id,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        score_value=score.score_value,
        source_count=score.source_count,
        recency_decay=score.recency_decay,
        corroboration_ratio=score.corroboration_ratio,
        capture_diversity=score.capture_diversity,
        reliability_weight_avg=score.reliability_weight_avg,
        computed_at=now,
    ).on_conflict_do_update(
        index_elements=["project_id", "entity_type", "entity_id"],
        set_={
            "score_value": score.score_value,
            "source_count": score.source_count,
            "recency_decay": score.recency_decay,
            "corroboration_ratio": score.corroboration_ratio,
            "capture_diversity": score.capture_diversity,
            "reliability_weight_avg": score.reliability_weight_avg,
            "computed_at": now,
        },
    )
    await session.execute(stmt)
    await session.flush()
    return score
