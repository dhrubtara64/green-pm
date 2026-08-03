"""Tests for Readiness Engine pipeline handler — S10-06."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.pipeline.handler as _handler_module
from app.pipeline.handler import (
    InvalidReadinessEventPayloadError,
    UnknownReadinessEventError,
    _READINESS_TOPIC,
    _SUBSCRIBED_EVENTS,
    handle_readiness_event,
)


@pytest.fixture
def session():
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.execute = AsyncMock()
    s.scalar = AsyncMock()
    return s


def _valid_payload(event_type: str = "activity.updated") -> dict:
    return {
        "event_type": event_type,
        "tenant_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
    }


class TestSubscribedEvents:
    def test_subscribed_events_is_frozenset(self):
        assert isinstance(_SUBSCRIBED_EVENTS, frozenset)

    def test_has_three_events(self):
        assert len(_SUBSCRIBED_EVENTS) == 3

    def test_supply_chain_readiness_updated_subscribed(self):
        assert "supply.chain.readiness.updated" in _SUBSCRIBED_EVENTS

    def test_activity_updated_subscribed(self):
        assert "activity.updated" in _SUBSCRIBED_EVENTS

    def test_evidence_score_computed_subscribed(self):
        assert "evidence.score.computed" in _SUBSCRIBED_EVENTS


class TestReadinessTopic:
    def test_topic_value(self):
        assert _READINESS_TOPIC == "greenpm.readiness"


class TestHandleReadinessEventUnknownEventType:
    @pytest.mark.asyncio
    async def test_unknown_event_type_raises(self, session):
        payload = _valid_payload("unknown.event")
        with pytest.raises(UnknownReadinessEventError):
            await handle_readiness_event(session, payload)

    @pytest.mark.asyncio
    async def test_empty_event_type_raises(self, session):
        payload = {**_valid_payload(), "event_type": ""}
        with pytest.raises(UnknownReadinessEventError):
            await handle_readiness_event(session, payload)


class TestHandleReadinessEventInvalidPayload:
    @pytest.mark.asyncio
    async def test_missing_project_id_raises(self, session):
        payload = {"event_type": "activity.updated", "tenant_id": str(uuid.uuid4())}
        with pytest.raises(InvalidReadinessEventPayloadError):
            await handle_readiness_event(session, payload)

    @pytest.mark.asyncio
    async def test_missing_tenant_id_raises(self, session):
        payload = {"event_type": "activity.updated", "project_id": str(uuid.uuid4())}
        with pytest.raises(InvalidReadinessEventPayloadError):
            await handle_readiness_event(session, payload)

    @pytest.mark.asyncio
    async def test_invalid_uuid_raises(self, session):
        payload = {
            "event_type": "activity.updated",
            "tenant_id": "not-a-uuid",
            "project_id": str(uuid.uuid4()),
        }
        with pytest.raises(InvalidReadinessEventPayloadError):
            await handle_readiness_event(session, payload)


class TestHandleReadinessEventSuccess:
    @pytest.mark.asyncio
    async def test_all_three_event_types_accepted(self, session):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        for event_type in _SUBSCRIBED_EVENTS:
            with patch.object(_handler_module, "write_outbox_event"):
                result = await handle_readiness_event(session, _valid_payload(event_type))
                assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_returns_gate_count(self, session):
        gate1 = MagicMock()
        gate1.id = uuid.uuid4()
        gate1.gate_type = "ENGINEERING"
        gate1.project_id = uuid.uuid4()
        gate1.status = "NOT_STARTED"
        gate1.completion_percentage = 0.0

        # list_gates execute → returns [gate1]
        mock_rows_list = MagicMock()
        mock_rows_list.scalars.return_value = [gate1]
        # recompute_gate_score → get_gate (scalar) + list_criteria (execute)
        mock_rows_criteria = MagicMock()
        mock_rows_criteria.scalars.return_value = []

        call_count = 0

        async def execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_rows_list
            return mock_rows_criteria

        session.execute.side_effect = execute_side_effect
        session.scalar.return_value = gate1

        with patch.object(_handler_module, "write_outbox_event"):
            result = await handle_readiness_event(session, _valid_payload("activity.updated"))
        assert result == 1

    @pytest.mark.asyncio
    async def test_outbox_event_emitted(self, session):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        with patch.object(_handler_module, "write_outbox_event") as mock_outbox:
            await handle_readiness_event(session, _valid_payload("activity.updated"))
            mock_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_outbox_topic_correct(self, session):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        with patch.object(_handler_module, "write_outbox_event") as mock_outbox:
            await handle_readiness_event(session, _valid_payload("evidence.score.computed"))
            call_kwargs = mock_outbox.call_args
            assert call_kwargs.kwargs.get("topic") == _READINESS_TOPIC or (
                call_kwargs.args and call_kwargs.args[1] == _READINESS_TOPIC
            )

    @pytest.mark.asyncio
    async def test_outbox_event_type_correct(self, session):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows

        with patch.object(_handler_module, "write_outbox_event") as mock_outbox:
            await handle_readiness_event(session, _valid_payload("supply.chain.readiness.updated"))
            _, kwargs = mock_outbox.call_args[0], mock_outbox.call_args[1]
            assert kwargs.get("event_type") == "ReadinessGateUpdated"
