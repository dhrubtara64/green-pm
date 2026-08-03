"""Tests for vendor scoring service — S8-01, S8-02, S8-03, S8-05."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scoring.schemas import DimensionScores
from app.scoring.service import (
    InvalidRFIStatusError,
    VendorScoreNotFoundError,
    compute_and_store_score,
    create_rfi,
    get_latest_score,
    get_score_history,
    get_trend,
    list_rfis,
)


_TENANT = uuid.uuid4()
_VENDOR = uuid.uuid4()
_PROJECT = uuid.uuid4()


def _ds(score: float = 75.0) -> DimensionScores:
    return DimensionScores(
        quality=score, delivery=score, responsiveness=score,
        documentation=score, commercial=score, relationship=score,
    )


def _make_session(scalar_value=None, scalars_value=None):
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=scalar_value)
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(scalars_value or [])
    session.execute = AsyncMock(return_value=result)
    return session


class TestComputeAndStoreScore:
    @pytest.mark.asyncio
    async def test_session_add_called(self):
        session = _make_session()
        await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self):
        session = _make_session()
        await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_vendor_score_record(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert result is not None

    @pytest.mark.asyncio
    async def test_record_has_uuid_id(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_overall_score_matches_uniform_dimensions(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds(80.0))
        assert pytest.approx(result.overall_score, abs=0.01) == 80.0

    @pytest.mark.asyncio
    async def test_vendor_id_stored(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert result.vendor_id == _VENDOR

    @pytest.mark.asyncio
    async def test_project_id_stored(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert result.project_id == _PROJECT

    @pytest.mark.asyncio
    async def test_computed_at_set(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert result.computed_at is not None

    @pytest.mark.asyncio
    async def test_dimension_scores_is_dict(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert isinstance(result.dimension_scores, dict)

    @pytest.mark.asyncio
    async def test_causal_attributions_empty_by_default(self):
        session = _make_session()
        result = await compute_and_store_score(session, _TENANT, _VENDOR, _PROJECT, _ds())
        assert result.causal_attributions == []

    @pytest.mark.asyncio
    async def test_causal_attributions_stored_when_provided(self):
        session = _make_session()
        attrs = [{"event_type": "test", "dimension": "quality", "score_delta": 5.0}]
        result = await compute_and_store_score(
            session, _TENANT, _VENDOR, _PROJECT, _ds(), causal_attributions=attrs
        )
        assert result.causal_attributions == attrs


class TestGetLatestScore:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = _make_session(scalar_value=None)
        result = await get_latest_score(session, _TENANT, _VENDOR)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_record_when_exists(self):
        mock_record = MagicMock()
        session = _make_session(scalar_value=mock_record)
        result = await get_latest_score(session, _TENANT, _VENDOR)
        assert result is mock_record


class TestGetScoreHistory:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none(self):
        session = _make_session(scalars_value=[])
        result = await get_score_history(session, _TENANT, _VENDOR)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_all_records(self):
        r1, r2 = MagicMock(), MagicMock()
        session = _make_session(scalars_value=[r1, r2])
        result = await get_score_history(session, _TENANT, _VENDOR)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_list(self):
        session = _make_session(scalars_value=[])
        result = await get_score_history(session, _TENANT, _VENDOR)
        assert isinstance(result, list)


class TestCreateRFI:
    @pytest.mark.asyncio
    async def test_session_add_called(self):
        session = _make_session()
        await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-001", "Clarify specs")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self):
        session = _make_session()
        await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-001", "Clarify specs")
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_rfi_status_is_open(self):
        session = _make_session()
        result = await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-001", "Clarify specs")
        assert result.status == "OPEN"

    @pytest.mark.asyncio
    async def test_rfi_number_stored(self):
        session = _make_session()
        result = await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-007", "Details")
        assert result.rfi_number == "RFI-007"

    @pytest.mark.asyncio
    async def test_rfi_title_stored(self):
        session = _make_session()
        result = await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-001", "Steel grade spec")
        assert result.title == "Steel grade spec"

    @pytest.mark.asyncio
    async def test_rfi_raised_at_set(self):
        session = _make_session()
        result = await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-001", "Title")
        assert result.raised_at is not None

    @pytest.mark.asyncio
    async def test_rfi_id_is_uuid(self):
        session = _make_session()
        result = await create_rfi(session, _TENANT, _VENDOR, _PROJECT, "RFI-001", "Title")
        assert isinstance(result.id, uuid.UUID)


class TestListRFIs:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none(self):
        session = _make_session(scalars_value=[])
        result = await list_rfis(session, _TENANT, _VENDOR)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_all_rfis(self):
        r1, r2 = MagicMock(), MagicMock()
        session = _make_session(scalars_value=[r1, r2])
        result = await list_rfis(session, _TENANT, _VENDOR)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_valid_status_filter_does_not_raise(self):
        session = _make_session(scalars_value=[])
        result = await list_rfis(session, _TENANT, _VENDOR, status="OPEN")
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_status_filter_raises(self):
        session = _make_session(scalars_value=[])
        with pytest.raises(InvalidRFIStatusError):
            await list_rfis(session, _TENANT, _VENDOR, status="INVALID")

    @pytest.mark.asyncio
    async def test_responded_status_filter_valid(self):
        session = _make_session(scalars_value=[])
        result = await list_rfis(session, _TENANT, _VENDOR, status="RESPONDED")
        assert result == []

    @pytest.mark.asyncio
    async def test_closed_status_filter_valid(self):
        session = _make_session(scalars_value=[])
        result = await list_rfis(session, _TENANT, _VENDOR, status="CLOSED")
        assert result == []
