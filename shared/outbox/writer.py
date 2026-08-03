"""Transactional outbox writer — shared by all domain services.

Any service that mutates state and wants to publish a domain event calls
write_outbox_event() inside the same transaction as the mutation. The
outbox-worker service picks up pending rows and publishes to Pub/Sub.

Never call commit() here — callers own the transaction boundary.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.outbox import OutboxEvent


async def write_outbox_event(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    topic: str,
    event_type: str,
    payload: dict[str, Any],
    schema_version: str = "1.0.0",
    correlation_id: Optional[uuid.UUID] = None,
    causation_id: Optional[uuid.UUID] = None,
) -> OutboxEvent:
    """Append a pending outbox event to the session (flush only, no commit)."""
    event = OutboxEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        topic=topic,
        event_type=event_type,
        schema_version=schema_version,
        payload=payload,
        status="pending",
        correlation_id=correlation_id,
        causation_id=causation_id,
        retry_count=0,
    )
    session.add(event)
    await session.flush()
    return event
