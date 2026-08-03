"""Outbox event publisher — S2-OUTBOX-01.

Reads pending outbox_events, publishes each to Pub/Sub, marks as published.
Uses the transactional outbox pattern: state changes are already committed
(written by the domain service), this worker only handles fan-out.

Guarantees:
- At-least-once delivery (retry on Pub/Sub failure, max_retries=5)
- Idempotent publish: Pub/Sub message ID is unique per attempt, consumer
  must deduplicate using the EventEnvelope.event_id (= outbox_event.id)
- Dead-letter: after max_retries, status → 'dead', last_error recorded
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.outbox import OutboxEvent

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_BATCH_SIZE = 50


class PubSubPublisher(Protocol):
    """Minimal interface so we can swap in a fake in tests."""

    async def publish(self, topic: str, data: bytes, attributes: dict[str, str]) -> str:
        """Publish message, return message_id."""
        ...


async def fetch_pending_events(
    session: AsyncSession,
    batch_size: int = _BATCH_SIZE,
) -> list[OutboxEvent]:
    """Fetch a batch of pending outbox events, oldest first."""
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == "pending")
        .order_by(OutboxEvent.created_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


def build_pubsub_message(event: OutboxEvent) -> tuple[bytes, dict[str, str]]:
    """Serialize an outbox event into (data_bytes, attributes) for Pub/Sub."""
    envelope = {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "tenant_id": str(event.tenant_id),
        "correlation_id": str(event.correlation_id) if event.correlation_id else None,
        "causation_id": str(event.causation_id) if event.causation_id else None,
        "occurred_at": event.created_at.isoformat() if hasattr(event.created_at, "isoformat") else str(event.created_at),
        "payload": event.payload,
    }
    data = json.dumps(envelope, default=str).encode("utf-8")
    attributes = {
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "tenant_id": str(event.tenant_id),
    }
    return data, attributes


async def mark_published(
    session: AsyncSession,
    event_id: uuid.UUID,
    message_id: str,
) -> None:
    now = datetime.now(timezone.utc)
    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(status="published", published_at=now, last_error=None)
    )


async def mark_failed(
    session: AsyncSession,
    event: OutboxEvent,
    error: str,
) -> None:
    new_retry = event.retry_count + 1
    new_status = "dead" if new_retry >= _MAX_RETRIES else "pending"
    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event.id)
        .values(
            retry_count=new_retry,
            last_error=error[:2000],
            status=new_status,
        )
    )
    if new_status == "dead":
        logger.error(
            "outbox_event_dead",
            extra={"event_id": str(event.id), "event_type": event.event_type, "error": error},
        )


async def process_batch(
    session: AsyncSession,
    publisher: PubSubPublisher,
    batch_size: int = _BATCH_SIZE,
) -> tuple[int, int]:
    """Fetch and publish one batch. Returns (published_count, failed_count)."""
    events = await fetch_pending_events(session, batch_size)
    published = failed = 0

    for event in events:
        data, attributes = build_pubsub_message(event)
        try:
            message_id = await publisher.publish(event.topic, data, attributes)
            await mark_published(session, event.id, message_id)
            published += 1
            logger.info(
                "outbox_event_published",
                extra={
                    "event_id": str(event.id),
                    "event_type": event.event_type,
                    "message_id": message_id,
                },
            )
        except Exception as exc:
            error_str = f"{type(exc).__name__}: {exc}"
            await mark_failed(session, event, error_str)
            failed += 1
            logger.warning(
                "outbox_event_failed",
                extra={
                    "event_id": str(event.id),
                    "retry_count": event.retry_count + 1,
                    "error": error_str,
                },
            )

    return published, failed


# Re-export from shared so callers have a single import path
from shared.outbox.writer import write_outbox_event  # noqa: F401
