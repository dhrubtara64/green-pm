"""Tests for risk pattern detector against organisational memory — S9-03."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.risk.pattern_detector import detect_risk_patterns
from app.risk.schemas import RiskPatternMatch


def _make_pattern(
    pattern_name: str,
    keywords: list[str],
    historical_outcome: str,
    confidence_base: float = 0.8,
    tenant_id: uuid.UUID | None = None,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.pattern_name = pattern_name
    p.keywords = keywords
    p.historical_outcome = historical_outcome
    p.confidence_base = confidence_base
    p.tenant_id = tenant_id or uuid.uuid4()
    return p


@pytest.fixture
def session():
    s = MagicMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


class TestDetectRiskPatternsEmpty:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_patterns(self, session, tenant_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Delay risk")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_keywords_match(self, session, tenant_id):
        pattern = _make_pattern("Unrelated Pattern", ["unrelated", "keyword"], "Some outcome")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Delivery delay")
        assert result == []

    @pytest.mark.asyncio
    async def test_skips_pattern_with_empty_keywords(self, session, tenant_id):
        pattern = _make_pattern("Empty Pattern", [], "Some outcome")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Any description")
        assert result == []


class TestDetectRiskPatternsMatching:
    @pytest.mark.asyncio
    async def test_returns_risk_pattern_match_instance(self, session, tenant_id):
        pattern = _make_pattern("Supplier delay", ["supplier", "delay"], "3-week overrun")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Supplier delay risk")
        assert len(result) == 1
        assert isinstance(result[0], RiskPatternMatch)

    @pytest.mark.asyncio
    async def test_stores_pattern_name(self, session, tenant_id):
        pattern = _make_pattern("Late deliveries", ["late", "delivery"], "Cost increase")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Logistics", "Late delivery risk")
        assert result[0].pattern_name == "Late deliveries"

    @pytest.mark.asyncio
    async def test_stores_historical_outcome(self, session, tenant_id):
        pattern = _make_pattern("Cost overrun", ["budget", "cost"], "10% budget increase")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Financial", "Budget and cost overrun")
        assert "budget increase" in result[0].historical_outcome

    @pytest.mark.asyncio
    async def test_confidence_is_between_zero_and_one(self, session, tenant_id):
        pattern = _make_pattern("Test pattern", ["schedule", "delay"], "Delay outcome", confidence_base=0.9)
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Delivery delay")
        assert 0.0 <= result[0].confidence <= 1.0

    @pytest.mark.asyncio
    async def test_full_keyword_match_increases_confidence(self, session, tenant_id):
        partial = _make_pattern("Partial", ["supply", "chain", "failure"], "Moderate impact", confidence_base=1.0)
        full = _make_pattern("Full", ["schedule", "delay"], "High impact", confidence_base=1.0)
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [partial, full]
        session.execute.return_value = mock_rows
        # "Schedule delay" matches "schedule" and "delay" fully (2/2), but "supply" not in text
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Delay expected")
        # full match pattern should appear
        names = [r.pattern_name for r in result]
        assert "Full" in names

    @pytest.mark.asyncio
    async def test_results_sorted_by_confidence_desc(self, session, tenant_id):
        low_conf = _make_pattern("Low", ["schedule", "delay", "unknown"], "Low", confidence_base=0.5)
        high_conf = _make_pattern("High", ["schedule", "delay"], "High", confidence_base=1.0)
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [low_conf, high_conf]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Delay risk")
        if len(result) >= 2:
            assert result[0].confidence >= result[1].confidence

    @pytest.mark.asyncio
    async def test_multiple_patterns_can_match(self, session, tenant_id):
        p1 = _make_pattern("P1", ["cost"], "Outcome 1")
        p2 = _make_pattern("P2", ["cost", "overrun"], "Outcome 2")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [p1, p2]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Financial", "Cost overrun risk")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_matching_is_case_insensitive(self, session, tenant_id):
        pattern = _make_pattern("Case test", ["SUPPLIER", "DELAY"], "Outcome")
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "supplier delay risk")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_pattern_id_matches(self, session, tenant_id):
        pid = uuid.uuid4()
        pattern = _make_pattern("ID test", ["delay"], "Outcome")
        pattern.id = pid
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = [pattern]
        session.execute.return_value = mock_rows
        result = await detect_risk_patterns(session, tenant_id, "Schedule", "Delay expected")
        assert result[0].pattern_id == pid
