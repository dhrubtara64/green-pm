"""Tests for Organizational Memory Engine service layer — S13-02–S13-06."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.memory.schemas import (
    HistoricalContextResponse,
    MemoryRecordCreate,
    PatternMatch,
    _MEMORY_CATEGORIES,
)
from app.memory.service import (
    MemoryRecordNotFoundError,
    get_historical_context,
    get_memory_record,
    list_memory_records,
    list_patterns,
    record_memory,
    search_patterns,
    upsert_pattern,
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


def _create(project_id: uuid.UUID, category: str = "DECISION", **kwargs) -> MemoryRecordCreate:
    return MemoryRecordCreate(project_id=project_id, category=category, summary="Test", **kwargs)


def _mock_rows(items) -> MagicMock:
    rows = MagicMock()
    rows.scalars.return_value = items
    return rows


def _mock_pattern(
    name: str = "Delay pattern",
    category: str = "VENDOR",
    confidence_score: float = 0.8,
    outcomes: list | None = None,
    trigger_conditions: dict | None = None,
    occurrence_count: int = 1,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.pattern_name = name
    p.category = category
    p.confidence_score = confidence_score
    p.historical_outcomes = outcomes or []
    p.trigger_conditions = trigger_conditions
    p.occurrence_count = occurrence_count
    return p


# ---------------------------------------------------------------------------
# record_memory
# ---------------------------------------------------------------------------

class TestRecordMemory:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await record_memory(session, tenant_id, _create(project_id))
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await record_memory(session, tenant_id, _create(project_id))
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_category_stored(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id, _create(project_id, "RISK"))
        assert rec.category == "RISK"

    @pytest.mark.asyncio
    async def test_summary_stored(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id,
                                  MemoryRecordCreate(project_id=project_id,
                                                     category="VENDOR",
                                                     summary="Vendor delay observed"))
        assert rec.summary == "Vendor delay observed"

    @pytest.mark.asyncio
    async def test_project_id_stored(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id, _create(project_id))
        assert rec.project_id == project_id

    @pytest.mark.asyncio
    async def test_tenant_id_stored(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id, _create(project_id))
        assert rec.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_confidence_score_stored(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id,
                                  _create(project_id, confidence_score=0.9))
        assert rec.confidence_score == pytest.approx(0.9, abs=1e-4)

    @pytest.mark.asyncio
    async def test_outcome_stored(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id,
                                  _create(project_id, outcome="Positive"))
        assert rec.outcome == "Positive"

    @pytest.mark.asyncio
    async def test_id_is_uuid(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id, _create(project_id))
        assert isinstance(rec.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_created_at_set(self, session, tenant_id, project_id):
        rec = await record_memory(session, tenant_id, _create(project_id))
        assert rec.created_at is not None


# ---------------------------------------------------------------------------
# get_memory_record
# ---------------------------------------------------------------------------

class TestGetMemoryRecord:
    @pytest.mark.asyncio
    async def test_returns_record_when_found(self, session, tenant_id):
        mock_rec = MagicMock()
        session.scalar.return_value = mock_rec
        result = await get_memory_record(session, tenant_id, uuid.uuid4())
        assert result is mock_rec

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(MemoryRecordNotFoundError):
            await get_memory_record(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_record_id(self, session, tenant_id):
        session.scalar.return_value = None
        rid = uuid.uuid4()
        with pytest.raises(MemoryRecordNotFoundError, match=str(rid)):
            await get_memory_record(session, tenant_id, rid)


# ---------------------------------------------------------------------------
# list_memory_records
# ---------------------------------------------------------------------------

class TestListMemoryRecords:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_memory_records(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_records(self, session, tenant_id, project_id):
        items = [MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_memory_records(session, tenant_id, project_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_category_filter_applied(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        await list_memory_records(session, tenant_id, project_id, category="RISK")
        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# upsert_pattern
# ---------------------------------------------------------------------------

class TestUpsertPattern:
    @pytest.mark.asyncio
    async def test_creates_new_pattern(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        pattern = await upsert_pattern(
            session, tenant_id, project_id,
            "VENDOR", "Delay pattern", {"type": "supply"}, "delayed", 0.8
        )
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert pattern.pattern_name == "Delay pattern"

    @pytest.mark.asyncio
    async def test_new_pattern_occurrence_count_is_one(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        pattern = await upsert_pattern(
            session, tenant_id, project_id,
            "RISK", "Risk pattern", None, "mitigated", 0.7
        )
        assert pattern.occurrence_count == 1

    @pytest.mark.asyncio
    async def test_new_pattern_historical_outcomes_contains_outcome(self, session, tenant_id, project_id):
        session.scalar.return_value = None
        pattern = await upsert_pattern(
            session, tenant_id, project_id,
            "DECISION", "Decision pattern", None, "approved", 0.9
        )
        assert "approved" in pattern.historical_outcomes

    @pytest.mark.asyncio
    async def test_existing_pattern_increments_occurrence_count(self, session, tenant_id, project_id):
        existing = _mock_pattern(occurrence_count=3, outcomes=["prev"])
        session.scalar.return_value = existing
        await upsert_pattern(
            session, tenant_id, project_id,
            "VENDOR", "Delay pattern", None, "new_outcome", 0.8
        )
        assert existing.occurrence_count == 4

    @pytest.mark.asyncio
    async def test_existing_pattern_appends_new_outcome(self, session, tenant_id, project_id):
        existing = _mock_pattern(outcomes=["prev_outcome"])
        session.scalar.return_value = existing
        await upsert_pattern(
            session, tenant_id, project_id,
            "VENDOR", "Delay pattern", None, "new_outcome", 0.8
        )
        assert "new_outcome" in existing.historical_outcomes

    @pytest.mark.asyncio
    async def test_existing_pattern_does_not_add_duplicate_outcome(self, session, tenant_id, project_id):
        existing = _mock_pattern(outcomes=["repeated"])
        session.scalar.return_value = existing
        await upsert_pattern(
            session, tenant_id, project_id,
            "VENDOR", "Delay pattern", None, "repeated", 0.8
        )
        assert existing.historical_outcomes.count("repeated") == 1

    @pytest.mark.asyncio
    async def test_existing_pattern_flushes(self, session, tenant_id, project_id):
        existing = _mock_pattern()
        session.scalar.return_value = existing
        await upsert_pattern(
            session, tenant_id, project_id,
            "VENDOR", "Delay pattern", None, "outcome", 0.8
        )
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_existing_pattern_not_added_again(self, session, tenant_id, project_id):
        existing = _mock_pattern()
        session.scalar.return_value = existing
        await upsert_pattern(
            session, tenant_id, project_id,
            "VENDOR", "Delay pattern", None, "outcome", 0.8
        )
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# list_patterns
# ---------------------------------------------------------------------------

class TestListPatterns:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await list_patterns(session, tenant_id, project_id=project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple_patterns(self, session, tenant_id):
        items = [MagicMock(), MagicMock(), MagicMock()]
        session.execute.return_value = _mock_rows(items)
        result = await list_patterns(session, tenant_id)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_category_filter_applied(self, session, tenant_id):
        session.execute.return_value = _mock_rows([])
        await list_patterns(session, tenant_id, category="RISK")
        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# search_patterns
# ---------------------------------------------------------------------------

class TestSearchPatterns:
    @pytest.mark.asyncio
    async def test_returns_list(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await search_patterns(session, tenant_id, project_id, ["delay"])
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_matching_pattern_returned(self, session, tenant_id, project_id):
        p = _mock_pattern(name="vendor delay", category="VENDOR")
        session.execute.return_value = _mock_rows([p])
        result = await search_patterns(session, tenant_id, project_id, ["vendor"])
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_non_matching_pattern_excluded(self, session, tenant_id, project_id):
        p = _mock_pattern(name="supply shortage")
        session.execute.return_value = _mock_rows([p])
        result = await search_patterns(session, tenant_id, project_id, ["budget"])
        assert result == []

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self, session, tenant_id, project_id):
        patterns = [_mock_pattern(name=f"vendor delay {i}") for i in range(10)]
        session.execute.return_value = _mock_rows(patterns)
        result = await search_patterns(session, tenant_id, project_id, ["vendor"], top_k=2)
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_returns_pattern_match_objects(self, session, tenant_id, project_id):
        p = _mock_pattern(name="vendor delay")
        session.execute.return_value = _mock_rows([p])
        result = await search_patterns(session, tenant_id, project_id, ["vendor"])
        assert all(isinstance(m, PatternMatch) for m in result)


# ---------------------------------------------------------------------------
# get_historical_context
# ---------------------------------------------------------------------------

class TestGetHistoricalContext:
    @pytest.mark.asyncio
    async def test_returns_list_of_historical_context_response(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_historical_context(
            session, tenant_id, project_id, "DECISION", ["approve"]
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_returns_historical_context_response_objects(self, session, tenant_id, project_id):
        p = _mock_pattern(name="approval pattern", category="DECISION",
                           outcomes=["approved"])
        session.execute.return_value = _mock_rows([p])
        result = await get_historical_context(
            session, tenant_id, project_id, "DECISION", ["approval"]
        )
        assert all(isinstance(r, HistoricalContextResponse) for r in result)

    @pytest.mark.asyncio
    async def test_empty_when_no_match(self, session, tenant_id, project_id):
        session.execute.return_value = _mock_rows([])
        result = await get_historical_context(
            session, tenant_id, project_id, "RISK", ["budget"]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self, session, tenant_id, project_id):
        patterns = [_mock_pattern(name=f"vendor delay {i}", category="VENDOR")
                    for i in range(10)]
        session.execute.return_value = _mock_rows(patterns)
        result = await get_historical_context(
            session, tenant_id, project_id, "VENDOR", ["vendor"], top_k=2
        )
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_response_has_pattern_name(self, session, tenant_id, project_id):
        p = _mock_pattern(name="Decision approval pattern", category="DECISION")
        session.execute.return_value = _mock_rows([p])
        result = await get_historical_context(
            session, tenant_id, project_id, "DECISION", ["approval"]
        )
        if result:
            assert result[0].pattern_name == "Decision approval pattern"

    @pytest.mark.asyncio
    async def test_response_has_historical_outcomes(self, session, tenant_id, project_id):
        p = _mock_pattern(name="approval pattern", category="DECISION",
                           outcomes=["outcome1", "outcome2"])
        session.execute.return_value = _mock_rows([p])
        result = await get_historical_context(
            session, tenant_id, project_id, "DECISION", ["approval"]
        )
        if result:
            assert "outcome1" in result[0].historical_outcomes
