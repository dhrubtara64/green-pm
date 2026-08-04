"""Tests for Recommendation Engine service layer — S16-01, S16-05."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.recommendation.schemas import RecommendationCreate
from app.recommendation.service import (
    RecommendationNotFoundError,
    create_recommendation,
    get_recommendation,
    list_recommendations,
    update_recommendation_status,
)


@pytest.fixture
def session():
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.scalar = AsyncMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


@pytest.fixture
def valid_create(project_id):
    return RecommendationCreate(
        project_id=project_id,
        engine_name="risk-engine",
        signal_type="RISK",
        priority_score=0.75,
        title="High-risk vendor delay",
        description="Vendor X delivery is 3 weeks late",
        projected_outcome="Milestone M3 slips 3 weeks",
        responsible_party="Procurement Lead",
        evidence_ids=[uuid.uuid4()],
    )


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestCreateRecommendation:
    @pytest.mark.asyncio
    async def test_add_called(self, session, tenant_id, valid_create):
        await create_recommendation(session, tenant_id, valid_create)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_called(self, session, tenant_id, valid_create):
        await create_recommendation(session, tenant_id, valid_create)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_recommendation(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result is not None

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert isinstance(result.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_status_is_active(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_created_at_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_tenant_id_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_project_id_set(self, session, tenant_id, valid_create, project_id):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_engine_name_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.engine_name == "risk-engine"

    @pytest.mark.asyncio
    async def test_title_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.title == "High-risk vendor delay"

    @pytest.mark.asyncio
    async def test_priority_score_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.priority_score == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_projected_outcome_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.projected_outcome == "Milestone M3 slips 3 weeks"

    @pytest.mark.asyncio
    async def test_responsible_party_set(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert result.responsible_party == "Procurement Lead"

    @pytest.mark.asyncio
    async def test_evidence_ids_serialized(self, session, tenant_id, valid_create):
        result = await create_recommendation(session, tenant_id, valid_create)
        assert isinstance(result.evidence_ids, list)

    @pytest.mark.asyncio
    async def test_ids_are_unique_per_call(self, session, tenant_id, valid_create):
        r1 = await create_recommendation(session, tenant_id, valid_create)
        r2 = await create_recommendation(session, tenant_id, valid_create)
        assert r1.id != r2.id


class TestListRecommendations:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_recommendations(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_called(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_recommendations(session, tenant_id, project_id)
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_ranked_results(self, session, tenant_id, project_id):
        items = [
            SimpleNamespace(priority_score=0.3, signal_type="RISK"),
            SimpleNamespace(priority_score=0.9, signal_type="DELAY"),
            SimpleNamespace(priority_score=0.6, signal_type="RISK"),
        ]
        session.execute.return_value = _mock_rows(items)
        result = await list_recommendations(session, tenant_id, project_id, top_n=3)
        assert result[0].priority_score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_top_n_applied(self, session, tenant_id, project_id):
        items = [SimpleNamespace(priority_score=float(i) / 10, signal_type="RISK") for i in range(15)]
        session.execute.return_value = _mock_rows(items)
        result = await list_recommendations(session, tenant_id, project_id, top_n=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_status_filter_accepted(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_recommendations(session, tenant_id, project_id, status="ACTIONED")
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_default_top_n_is_ten(self, session, tenant_id, project_id):
        items = [SimpleNamespace(priority_score=float(i) / 20, signal_type="RISK") for i in range(20)]
        session.execute.return_value = _mock_rows(items)
        result = await list_recommendations(session, tenant_id, project_id)
        assert len(result) == 10


class TestGetRecommendation:
    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_recommendation(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(RecommendationNotFoundError):
            await get_recommendation(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_contains_id(self, session, tenant_id):
        session.scalar.return_value = None
        rid = uuid.uuid4()
        with pytest.raises(RecommendationNotFoundError, match=str(rid)):
            await get_recommendation(session, tenant_id, rid)

    @pytest.mark.asyncio
    async def test_scalar_called(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await get_recommendation(session, tenant_id, uuid.uuid4())
        session.scalar.assert_awaited_once()


class TestUpdateRecommendationStatus:
    @pytest.mark.asyncio
    async def test_updates_status(self, session, tenant_id):
        mock_rec = MagicMock()
        mock_rec.status = "ACTIVE"
        session.scalar.return_value = mock_rec
        result = await update_recommendation_status(session, tenant_id, uuid.uuid4(), "ACTIONED")
        assert mock_rec.status == "ACTIONED"

    @pytest.mark.asyncio
    async def test_flush_called(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await update_recommendation_status(session, tenant_id, uuid.uuid4(), "DISMISSED")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await update_recommendation_status(session, tenant_id, uuid.uuid4(), "ACTIONED")
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(RecommendationNotFoundError):
            await update_recommendation_status(session, tenant_id, uuid.uuid4(), "ACTIONED")

    @pytest.mark.asyncio
    async def test_dismissed_status_set(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        await update_recommendation_status(session, tenant_id, uuid.uuid4(), "DISMISSED")
        assert mock_rec.status == "DISMISSED"
