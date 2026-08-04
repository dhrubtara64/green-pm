"""Tests for Synchronization & Consistency Engine service layer — S15-06."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.sync.schemas import ConsistencyReportResponse, InconsistencyResponse
from app.sync.service import (
    InconsistencyNotFoundError,
    get_consistency_report,
    list_inconsistencies,
    resolve_inconsistency,
    run_consistency_check,
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


def _conflicting_edges(a: uuid.UUID, b: uuid.UUID) -> list[dict]:
    return [
        {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.1},
        {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.9},
    ]


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


class TestRunConsistencyCheck:
    @pytest.mark.asyncio
    async def test_empty_edges_returns_empty(self, session, tenant_id, project_id):
        result = await run_consistency_check(session, tenant_id, project_id, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_contradiction_returns_empty(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        # delta = 0.1, below threshold
        edges = [
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.3},
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.4},
        ]
        result = await run_consistency_check(session, tenant_id, project_id, edges)
        assert result == []
        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_contradiction_detected_add_called(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        await run_consistency_check(
            session, tenant_id, project_id, _conflicting_edges(a, b)
        )
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_contradiction_detected_flush_called(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        await run_consistency_check(
            session, tenant_id, project_id, _conflicting_edges(a, b)
        )
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_list_of_records(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        result = await run_consistency_check(
            session, tenant_id, project_id, _conflicting_edges(a, b)
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_record_has_delta(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        result = await run_consistency_check(
            session, tenant_id, project_id, _conflicting_edges(a, b)
        )
        assert result[0].delta == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_record_id_is_uuid(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        result = await run_consistency_check(
            session, tenant_id, project_id, _conflicting_edges(a, b)
        )
        assert isinstance(result[0].id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_record_flagged_at_set(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        result = await run_consistency_check(
            session, tenant_id, project_id, _conflicting_edges(a, b)
        )
        assert result[0].flagged_at is not None

    @pytest.mark.asyncio
    async def test_custom_threshold_applied(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        # delta = 0.3
        edges = [
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.3},
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.6},
        ]
        result = await run_consistency_check(
            session, tenant_id, project_id, edges, threshold=0.4
        )
        assert result == []


class TestResolveInconsistency:
    @pytest.mark.asyncio
    async def test_sets_resolved_at(self, session, tenant_id):
        mock_rec = MagicMock()
        mock_rec.resolved_at = None
        session.scalar.return_value = mock_rec
        await resolve_inconsistency(session, tenant_id, uuid.uuid4())
        assert mock_rec.resolved_at is not None

    @pytest.mark.asyncio
    async def test_flushes(self, session, tenant_id):
        session.scalar.return_value = MagicMock()
        await resolve_inconsistency(session, tenant_id, uuid.uuid4())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_record(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await resolve_inconsistency(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(InconsistencyNotFoundError):
            await resolve_inconsistency(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_id(self, session, tenant_id):
        session.scalar.return_value = None
        iid = uuid.uuid4()
        with pytest.raises(InconsistencyNotFoundError, match=str(iid)):
            await resolve_inconsistency(session, tenant_id, iid)


class TestListInconsistencies:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_inconsistencies(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_records(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_inconsistencies(session, tenant_id, project_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_execute_called(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_inconsistencies(session, tenant_id, project_id)
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolved_flag_changes_query(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_inconsistencies(session, tenant_id, project_id, resolved=True)
        session.execute.assert_awaited_once()


class TestGetConsistencyReport:
    @pytest.mark.asyncio
    async def test_returns_consistency_report_response(self, session, tenant_id, project_id):
        result = await get_consistency_report(session, tenant_id, project_id, [])
        assert isinstance(result, ConsistencyReportResponse)

    @pytest.mark.asyncio
    async def test_empty_edges_zero_counts(self, session, tenant_id, project_id):
        result = await get_consistency_report(session, tenant_id, project_id, [])
        assert result.total_edges_checked == 0
        assert result.inconsistencies_found == 0
        assert result.inconsistencies == []

    @pytest.mark.asyncio
    async def test_total_edges_checked_correct(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.3},
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.4},
        ]
        result = await get_consistency_report(session, tenant_id, project_id, edges)
        assert result.total_edges_checked == 2

    @pytest.mark.asyncio
    async def test_inconsistencies_found_correct(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.1},
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.9},
        ]
        result = await get_consistency_report(session, tenant_id, project_id, edges)
        assert result.inconsistencies_found == 1

    @pytest.mark.asyncio
    async def test_inconsistency_responses_are_correct_type(self, session, tenant_id, project_id):
        a, b = uuid.uuid4(), uuid.uuid4()
        edges = [
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.1},
            {"entity_a_id": a, "entity_b_id": b, "edge_type": "dep", "weight": 0.9},
        ]
        result = await get_consistency_report(session, tenant_id, project_id, edges)
        assert all(isinstance(r, InconsistencyResponse) for r in result.inconsistencies)
