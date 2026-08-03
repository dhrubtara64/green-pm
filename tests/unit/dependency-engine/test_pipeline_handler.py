"""Unit tests for activity.updated pipeline handler — S6-04, S6-06."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.handler import (
    InvalidActivityPayloadError,
    _CPM_TOPIC,
    handle_activity_updated,
    parse_activity_updated_payload,
)


_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_ACTIVITY = uuid.uuid4()

_VALID_PAYLOAD = {
    "project_id": str(_PROJECT),
    "tenant_id": str(_TENANT),
    "activity_id": str(_ACTIVITY),
}


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_cpm_topic_is_greenpm_cpm(self):
        assert _CPM_TOPIC == "greenpm.cpm"


# ──────────────────────────────────────────────────────────────────────────────
# parse_activity_updated_payload
# ──────────────────────────────────────────────────────────────────────────────

class TestParseActivityUpdatedPayload:
    def test_valid_payload_returns_dict(self):
        result = parse_activity_updated_payload(_VALID_PAYLOAD)
        assert isinstance(result, dict)

    def test_project_id_parsed_as_uuid(self):
        result = parse_activity_updated_payload(_VALID_PAYLOAD)
        assert result["project_id"] == _PROJECT

    def test_tenant_id_parsed_as_uuid(self):
        result = parse_activity_updated_payload(_VALID_PAYLOAD)
        assert result["tenant_id"] == _TENANT

    def test_activity_id_parsed_when_present(self):
        result = parse_activity_updated_payload(_VALID_PAYLOAD)
        assert result["activity_id"] == _ACTIVITY

    def test_activity_id_none_when_absent(self):
        payload = {"project_id": str(_PROJECT), "tenant_id": str(_TENANT)}
        result = parse_activity_updated_payload(payload)
        assert result["activity_id"] is None

    def test_empty_payload_raises(self):
        with pytest.raises(InvalidActivityPayloadError):
            parse_activity_updated_payload({})

    def test_missing_project_id_raises(self):
        with pytest.raises(InvalidActivityPayloadError) as exc:
            parse_activity_updated_payload({"tenant_id": str(_TENANT)})
        assert "project_id" in str(exc.value)

    def test_missing_tenant_id_raises(self):
        with pytest.raises(InvalidActivityPayloadError) as exc:
            parse_activity_updated_payload({"project_id": str(_PROJECT)})
        assert "tenant_id" in str(exc.value)

    def test_invalid_uuid_for_project_id_raises(self):
        with pytest.raises(InvalidActivityPayloadError):
            parse_activity_updated_payload(
                {"project_id": "not-a-uuid", "tenant_id": str(_TENANT)}
            )


# ──────────────────────────────────────────────────────────────────────────────
# handle_activity_updated
# ──────────────────────────────────────────────────────────────────────────────

import app.pipeline.handler as _handler_mod


class TestHandleActivityUpdated:
    def _make_cpm_result(self) -> MagicMock:
        r = MagicMock()
        r.id = uuid.uuid4()
        r.project_id = _PROJECT
        r.project_duration = 10.0
        r.critical_path_activity_ids = [str(_ACTIVITY)]
        r.near_critical_activity_ids = []
        return r

    @pytest.mark.asyncio
    async def test_calls_run_cpm_for_project(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()),
        ):
            await handle_activity_updated(session, _VALID_PAYLOAD)
            _handler_mod.run_cpm_for_project.assert_called_once_with(
                session, _TENANT, _PROJECT
            )

    @pytest.mark.asyncio
    async def test_emits_outbox_event(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_activity_updated(session, _VALID_PAYLOAD)
            mock_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_outbox_event_type_is_critical_path_recomputed(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_activity_updated(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            assert kwargs.get("event_type") == "CriticalPathRecomputed"

    @pytest.mark.asyncio
    async def test_outbox_topic_is_greenpm_cpm(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_activity_updated(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            assert kwargs.get("topic") == "greenpm.cpm"

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_project_duration(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_activity_updated(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            payload = kwargs.get("payload", {})
            assert "project_duration" in payload
            assert payload["project_duration"] == pytest.approx(10.0)

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_near_critical_count(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()) as mock_outbox,
        ):
            await handle_activity_updated(session, _VALID_PAYLOAD)
            _, kwargs = mock_outbox.call_args
            payload = kwargs.get("payload", {})
            assert "near_critical_count" in payload

    @pytest.mark.asyncio
    async def test_returns_cpm_result(self):
        mock_result = self._make_cpm_result()
        session = AsyncMock()
        with (
            patch.object(_handler_mod, "run_cpm_for_project", AsyncMock(return_value=mock_result)),
            patch.object(_handler_mod, "write_outbox_event", AsyncMock()),
        ):
            returned = await handle_activity_updated(session, _VALID_PAYLOAD)
            assert returned is mock_result
