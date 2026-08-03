"""Outbox publisher unit tests — S2-OUTBOX-01."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from app.publisher import (
    _MAX_RETRIES,
    build_pubsub_message,
    mark_failed,
    mark_published,
    process_batch,
    write_outbox_event,
)


def _make_event(
    status="pending",
    retry_count=0,
    event_type="ActivityDelayed",
    topic="greenpm.activities",
) -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.tenant_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    e.topic = topic
    e.event_type = event_type
    e.schema_version = "1.0.0"
    e.correlation_id = uuid.uuid4()
    e.causation_id = None
    e.payload = {"activity_id": str(uuid.uuid4())}
    e.status = status
    e.retry_count = retry_count
    e.created_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    return e


# ── build_pubsub_message ──────────────────────────────────────────────────────

def test_build_pubsub_message_valid_json():
    event = _make_event()
    data, attrs = build_pubsub_message(event)
    envelope = json.loads(data)
    assert envelope["event_id"] == str(event.id)
    assert envelope["event_type"] == event.event_type
    assert envelope["schema_version"] == "1.0.0"
    assert envelope["tenant_id"] == str(event.tenant_id)
    assert "payload" in envelope


def test_build_pubsub_message_attributes():
    event = _make_event()
    _, attrs = build_pubsub_message(event)
    assert attrs["event_type"] == event.event_type
    assert attrs["tenant_id"] == str(event.tenant_id)


def test_build_pubsub_message_causation_id_none():
    event = _make_event()
    event.causation_id = None
    data, _ = build_pubsub_message(event)
    envelope = json.loads(data)
    assert envelope["causation_id"] is None


def test_build_pubsub_message_envelope_is_valid_utf8():
    event = _make_event()
    data, _ = build_pubsub_message(event)
    # Must decode without error and round-trip
    decoded = json.loads(data.decode("utf-8"))
    assert decoded["event_type"] == event.event_type


# ── write_outbox_event ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_write_outbox_event_creates_pending():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    tenant_id = uuid.uuid4()

    result = await write_outbox_event(
        session,
        tenant_id=tenant_id,
        topic="greenpm.activities",
        event_type="ActivityDelayed",
        payload={"delay_days": 3},
    )

    assert result.status == "pending"
    assert result.retry_count == 0
    assert result.tenant_id == tenant_id
    session.add.assert_called_once_with(result)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_write_outbox_event_unique_ids():
    s1, s2 = AsyncMock(), AsyncMock()
    s1.add = MagicMock(); s1.flush = AsyncMock()
    s2.add = MagicMock(); s2.flush = AsyncMock()
    tenant_id = uuid.uuid4()

    e1 = await write_outbox_event(s1, tenant_id=tenant_id, topic="t", event_type="X", payload={})
    e2 = await write_outbox_event(s2, tenant_id=tenant_id, topic="t", event_type="X", payload={})
    assert e1.id != e2.id


@pytest.mark.asyncio
async def test_write_outbox_event_propagates_correlation_id():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    corr_id = uuid.uuid4()

    result = await write_outbox_event(
        session,
        tenant_id=uuid.uuid4(),
        topic="t",
        event_type="X",
        payload={},
        correlation_id=corr_id,
    )
    assert result.correlation_id == corr_id


# ── process_batch ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_batch_all_succeed():
    events = [_make_event() for _ in range(3)]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result] + [AsyncMock()] * 3)

    publisher = AsyncMock()
    publisher.publish = AsyncMock(return_value="msg-id-ok")

    published, failed = await process_batch(session, publisher, batch_size=10)
    assert published == 3
    assert failed == 0


@pytest.mark.asyncio
async def test_process_batch_handles_publish_failure():
    event = _make_event()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [event]

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[mock_result, AsyncMock()])

    publisher = AsyncMock()
    publisher.publish = AsyncMock(side_effect=Exception("Pub/Sub unavailable"))

    published, failed = await process_batch(session, publisher, batch_size=10)
    assert published == 0
    assert failed == 1


@pytest.mark.asyncio
async def test_process_batch_empty_returns_zeros():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    publisher = AsyncMock()

    published, failed = await process_batch(session, publisher)
    assert published == 0
    assert failed == 0
    publisher.publish.assert_not_called()


# ── mark_failed — dead-letter after max retries ───────────────────────────────

@pytest.mark.asyncio
async def test_mark_failed_transitions_to_dead_at_max_retries():
    event = _make_event(retry_count=_MAX_RETRIES - 1)
    session = AsyncMock()
    await mark_failed(session, event, "boom")

    stmt = session.execute.call_args[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "dead" in compiled


@pytest.mark.asyncio
async def test_mark_failed_stays_pending_before_max_retries():
    event = _make_event(retry_count=0)
    session = AsyncMock()
    await mark_failed(session, event, "temporary error")

    stmt = session.execute.call_args[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "pending" in compiled


def test_max_retries_constant():
    assert _MAX_RETRIES == 5
