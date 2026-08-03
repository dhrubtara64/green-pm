"""Unit tests for stage transition pipeline handler — S7-06."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.handler import (
    InvalidStageTransitionPayloadError,
    _SUPPLY_TOPIC,
    handle_stage_transition,
    parse_stage_transition_payload,
)


_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_DISPATCH = uuid.uuid4()

_VALID_PAYLOAD = {
    "dispatch_id": str(_DISPATCH),
    "tenant_id": str(_TENANT),
    "project_id": str(_PROJECT),
    "target_stage": "VENDOR_CONFIRMED",
}


class TestConstants:
    def test_supply_topic_is_greenpm_supply(self):
        assert _SUPPLY_TOPIC == "greenpm.supply"


class TestParseStageTransitionPayload:
    def test_valid_payload_returns_dict(self):
        result = parse_stage_transition_payload(_VALID_PAYLOAD)
        assert isinstance(result, dict)

    def test_dispatch_id_parsed_as_uuid(self):
        result = parse_stage_transition_payload(_VALID_PAYLOAD)
        assert result["dispatch_id"] == _DISPATCH

    def test_tenant_id_parsed_as_uuid(self):
        result = parse_stage_transition_payload(_VALID_PAYLOAD)
        assert result["tenant_id"] == _TENANT

    def test_project_id_parsed_as_uuid(self):
        result = parse_stage_transition_payload(_VALID_PAYLOAD)
        assert result["project_id"] == _PROJECT

    def test_target_stage_stored_as_str(self):
        result = parse_stage_transition_payload(_VALID_PAYLOAD)
        assert result["target_stage"] == "VENDOR_CONFIRMED"

    def test_empty_payload_raises(self):
        with pytest.raises(InvalidStageTransitionPayloadError):
            parse_stage_transition_payload({})

    def test_missing_dispatch_id_raises(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "dispatch_id"}
        with pytest.raises(InvalidStageTransitionPayloadError) as exc:
            parse_stage_transition_payload(payload)
        assert "dispatch_id" in str(exc.value)

    def test_missing_tenant_id_raises(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "tenant_id"}
        with pytest.raises(InvalidStageTransitionPayloadError) as exc:
            parse_stage_transition_payload(payload)
        assert "tenant_id" in str(exc.value)

    def test_missing_project_id_raises(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "project_id"}
        with pytest.raises(InvalidStageTransitionPayloadError) as exc:
            parse_stage_transition_payload(payload)
        assert "project_id" in str(exc.value)

    def test_missing_target_stage_raises(self):
        payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "target_stage"}
        with pytest.raises(InvalidStageTransitionPayloadError):
            parse_stage_transition_payload(payload)

    def test_invalid_uuid_for_dispatch_id_raises(self):
        payload = {**_VALID_PAYLOAD, "dispatch_id": "not-a-uuid"}
        with pytest.raises(InvalidStageTransitionPayloadError):
            parse_stage_transition_payload(payload)

    def test_invalid_uuid_for_tenant_id_raises(self):
        payload = {**_VALID_PAYLOAD, "tenant_id": "bad"}
        with pytest.raises(InvalidStageTransitionPayloadError):
            parse_stage_transition_payload(payload)


import app.pipeline.handler as _handler_mod


class TestHandleStageTransition:
    def _make_dispatch(self):
        d = MagicMock()
        d.id = _DISPATCH
        d.current_stage = "VENDOR_CONFIRMED"
        d.material_readiness_score = 11.11
        d.critical_material_count = 0
        return d

    @pytest.mark.asyncio
    async def test_calls_transition_dispatch_stage(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()),
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _handler_mod.transition_dispatch_stage.assert_called_once_with(
                session, _TENANT, _DISPATCH, "VENDOR_CONFIRMED"
            )

    @pytest.mark.asyncio
    async def test_emits_outbox_event(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            mock_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_outbox_event_type_is_supply_chain_readiness_updated(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            assert kwargs.get("event_type") == "SupplyChainReadinessUpdated"

    @pytest.mark.asyncio
    async def test_outbox_topic_is_greenpm_supply(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            assert kwargs.get("topic") == "greenpm.supply"

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_new_stage(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            payload = kwargs.get("payload", {})
            assert payload.get("new_stage") == "VENDOR_CONFIRMED"

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_readiness_score(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            payload = kwargs.get("payload", {})
            assert "material_readiness_score" in payload

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_critical_material_count(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            payload = kwargs.get("payload", {})
            assert "critical_material_count" in payload

    @pytest.mark.asyncio
    async def test_returns_dispatch(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()),
        ):
            returned = await handle_stage_transition(session, _VALID_PAYLOAD)
            assert returned is mock_dispatch

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_dispatch_id(self):
        mock_dispatch = self._make_dispatch()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "transition_dispatch_stage", AsyncMock(return_value=mock_dispatch)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_stage_transition(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            payload = kwargs.get("payload", {})
            assert payload.get("dispatch_id") == str(_DISPATCH)
