"""Unit tests for Evidence Review service — S4-01 + S4-05."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.reviews.service as _rsvc
from app.evidence.service import EvidenceNotFoundError
from app.reviews.schemas import EvidenceReviewCreate
from app.reviews.service import EvidenceReviewError, create_review, list_reviews

_TENANT = uuid.uuid4()
_PROJECT = uuid.uuid4()
_REVIEWER = uuid.uuid4()
_EVIDENCE_ID = uuid.uuid4()
_ENTITY = uuid.uuid4()


def _make_evidence(status="submitted", **kwargs):
    defaults = dict(
        id=_EVIDENCE_ID,
        project_id=_PROJECT,
        tenant_id=_TENANT,
        entity_type="activity",
        entity_id=_ENTITY,
        capture_type="site_photo",
        status=status,
        reliability_tier="secondary",
        evidence_metadata={},
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_session():
    s = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    return s


def _review_create(outcome="approved", **kwargs):
    return EvidenceReviewCreate(outcome=outcome, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# create_review — happy paths
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateReview:
    @pytest.mark.asyncio
    async def test_adds_review_to_session(self):
        session = _make_session()
        ev = _make_evidence()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create())
        assert session.add.called

    @pytest.mark.asyncio
    async def test_approved_transitions_evidence_status(self):
        session = _make_session()
        ev = _make_evidence(status="submitted")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("approved"))
        assert ev.status == "approved"

    @pytest.mark.asyncio
    async def test_rejected_transitions_evidence_status(self):
        session = _make_session()
        ev = _make_evidence(status="submitted")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("rejected"))
        assert ev.status == "rejected"

    @pytest.mark.asyncio
    async def test_needs_revision_transitions_to_under_review(self):
        session = _make_session()
        ev = _make_evidence(status="submitted")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("needs_revision"))
        assert ev.status == "under_review"

    @pytest.mark.asyncio
    async def test_review_from_under_review_allowed(self):
        session = _make_session()
        ev = _make_evidence(status="under_review")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            result = await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("approved"))
        assert result is not None

    @pytest.mark.asyncio
    async def test_outbox_event_emitted_with_correct_type(self):
        session = _make_session()
        ev = _make_evidence()
        mock_outbox = AsyncMock()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", mock_outbox),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create())
        mock_outbox.assert_called_once()
        assert mock_outbox.call_args.kwargs["event_type"] == "EvidenceReviewed"

    @pytest.mark.asyncio
    async def test_outbox_payload_contains_outcome(self):
        session = _make_session()
        ev = _make_evidence()
        mock_outbox = AsyncMock()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", mock_outbox),
            patch.object(_rsvc, "compute_and_store_score", AsyncMock()),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("rejected"))
        payload = mock_outbox.call_args.kwargs["payload"]
        assert payload["outcome"] == "rejected"


# ──────────────────────────────────────────────────────────────────────────────
# create_review — S4-05: score recomputation
# ──────────────────────────────────────────────────────────────────────────────

class TestScoreRecomputation:
    @pytest.mark.asyncio
    async def test_score_recomputed_on_approved(self):
        session = _make_session()
        ev = _make_evidence()
        mock_score = AsyncMock()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", mock_score),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("approved"))
        mock_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_recomputed_on_rejected(self):
        session = _make_session()
        ev = _make_evidence()
        mock_score = AsyncMock()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", mock_score),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("rejected"))
        mock_score.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_not_recomputed_on_needs_revision(self):
        session = _make_session()
        ev = _make_evidence()
        mock_score = AsyncMock()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", mock_score),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("needs_revision"))
        mock_score.assert_not_called()

    @pytest.mark.asyncio
    async def test_score_recompute_uses_correct_entity(self):
        session = _make_session()
        ev = _make_evidence(entity_type="milestone", entity_id=_ENTITY)
        mock_score = AsyncMock()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
            patch.object(_rsvc, "write_outbox_event", AsyncMock()),
            patch.object(_rsvc, "compute_and_store_score", mock_score),
        ):
            await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create("approved"))
        call_kwargs = mock_score.call_args
        assert call_kwargs.args[3] == "milestone"
        assert call_kwargs.args[4] == _ENTITY


# ──────────────────────────────────────────────────────────────────────────────
# create_review — invalid state
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateReviewGuards:
    @pytest.mark.asyncio
    async def test_approved_evidence_cannot_be_reviewed(self):
        session = _make_session()
        ev = _make_evidence(status="approved")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
        ):
            with pytest.raises(EvidenceReviewError):
                await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create())

    @pytest.mark.asyncio
    async def test_rejected_evidence_cannot_be_reviewed(self):
        session = _make_session()
        ev = _make_evidence(status="rejected")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
        ):
            with pytest.raises(EvidenceReviewError):
                await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create())

    @pytest.mark.asyncio
    async def test_archived_evidence_cannot_be_reviewed(self):
        session = _make_session()
        ev = _make_evidence(status="archived")
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(return_value=ev)),
        ):
            with pytest.raises(EvidenceReviewError):
                await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create())

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        session = _make_session()
        with (
            patch.object(_rsvc, "get_evidence", AsyncMock(side_effect=EvidenceNotFoundError(uuid.uuid4()))),
        ):
            with pytest.raises(EvidenceNotFoundError):
                await create_review(session, _TENANT, _REVIEWER, _EVIDENCE_ID, _review_create())


# ──────────────────────────────────────────────────────────────────────────────
# list_reviews
# ──────────────────────────────────────────────────────────────────────────────

class TestListReviews:
    @pytest.mark.asyncio
    async def test_returns_sequence(self):
        session = _make_session()
        mock_review = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_review]
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_reviews(session, _TENANT, _EVIDENCE_ID)
        assert list(result) == [mock_review]

    @pytest.mark.asyncio
    async def test_returns_empty(self):
        session = _make_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)
        result = await list_reviews(session, _TENANT, _EVIDENCE_ID)
        assert list(result) == []
