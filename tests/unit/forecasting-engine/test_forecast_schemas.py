"""Tests for Forecasting Engine schemas — S14-01, S14-03."""
import uuid
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from app.forecast.schemas import (
    ForecastDomainCreate,
    ForecastQuery,
    ForecastResponse,
    ForecastSummaryResponse,
    _FORECAST_DOMAINS,
    _TREND_DIRECTIONS,
)


class TestForecastDomainsConstant:
    def test_is_frozenset(self):
        assert isinstance(_FORECAST_DOMAINS, frozenset)

    def test_has_six_domains(self):
        assert len(_FORECAST_DOMAINS) == 6

    def test_schedule_present(self):
        assert "SCHEDULE" in _FORECAST_DOMAINS

    def test_budget_present(self):
        assert "BUDGET" in _FORECAST_DOMAINS

    def test_quality_present(self):
        assert "QUALITY" in _FORECAST_DOMAINS

    def test_resource_present(self):
        assert "RESOURCE" in _FORECAST_DOMAINS

    def test_commissioning_present(self):
        assert "COMMISSIONING" in _FORECAST_DOMAINS

    def test_cash_flow_present(self):
        assert "CASH_FLOW" in _FORECAST_DOMAINS


class TestTrendDirectionsConstant:
    def test_is_frozenset(self):
        assert isinstance(_TREND_DIRECTIONS, frozenset)

    def test_has_three_directions(self):
        assert len(_TREND_DIRECTIONS) == 3

    def test_up_present(self):
        assert "UP" in _TREND_DIRECTIONS

    def test_down_present(self):
        assert "DOWN" in _TREND_DIRECTIONS

    def test_stable_present(self):
        assert "STABLE" in _TREND_DIRECTIONS


class TestForecastQuery:
    def _make(self, **kw) -> ForecastQuery:
        base = dict(project_id=uuid.uuid4(), domain="SCHEDULE")
        return ForecastQuery(**{**base, **kw})

    def test_stores_project_id(self):
        pid = uuid.uuid4()
        assert self._make(project_id=pid).project_id == pid

    def test_stores_domain(self):
        assert self._make(domain="BUDGET").domain == "BUDGET"

    def test_is_frozen(self):
        q = self._make()
        with pytest.raises(FrozenInstanceError):
            q.domain = "RISK"  # type: ignore[misc]

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError, match="domain"):
            self._make(domain="BOGUS")

    def test_all_valid_domains(self):
        for d in _FORECAST_DOMAINS:
            q = self._make(domain=d)
            assert q.domain == d


class TestForecastDomainCreate:
    def _pid(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_stores_project_id(self):
        pid = self._pid()
        c = ForecastDomainCreate(
            project_id=pid, domain="SCHEDULE", current_value=100.0, forecast_value=95.0
        )
        assert c.project_id == pid

    def test_stores_domain(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="BUDGET", current_value=0.0, forecast_value=0.0
        )
        assert c.domain == "BUDGET"

    def test_stores_current_value(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="QUALITY", current_value=42.5, forecast_value=0.0
        )
        assert c.current_value == pytest.approx(42.5)

    def test_stores_forecast_value(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="RESOURCE", current_value=0.0, forecast_value=88.0
        )
        assert c.forecast_value == pytest.approx(88.0)

    def test_default_confidence(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="COMMISSIONING", current_value=0.0, forecast_value=0.0
        )
        assert c.confidence == pytest.approx(0.5)

    def test_default_trend_stable(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="CASH_FLOW", current_value=0.0, forecast_value=0.0
        )
        assert c.trend == "STABLE"

    def test_invalid_domain_raises(self):
        with pytest.raises(ValidationError):
            ForecastDomainCreate(
                project_id=self._pid(), domain="BOGUS", current_value=0.0, forecast_value=0.0
            )

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            ForecastDomainCreate(
                project_id=self._pid(), domain="SCHEDULE",
                current_value=0.0, forecast_value=0.0, confidence=1.1
            )

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            ForecastDomainCreate(
                project_id=self._pid(), domain="BUDGET",
                current_value=0.0, forecast_value=0.0, confidence=-0.1
            )

    def test_invalid_trend_raises(self):
        with pytest.raises(ValidationError):
            ForecastDomainCreate(
                project_id=self._pid(), domain="QUALITY",
                current_value=0.0, forecast_value=0.0, trend="SIDEWAYS"
            )

    def test_confidence_zero_valid(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="SCHEDULE",
            current_value=0.0, forecast_value=0.0, confidence=0.0
        )
        assert c.confidence == 0.0

    def test_confidence_one_valid(self):
        c = ForecastDomainCreate(
            project_id=self._pid(), domain="SCHEDULE",
            current_value=0.0, forecast_value=0.0, confidence=1.0
        )
        assert c.confidence == 1.0

    def test_all_valid_trends(self):
        for t in _TREND_DIRECTIONS:
            c = ForecastDomainCreate(
                project_id=self._pid(), domain="BUDGET",
                current_value=0.0, forecast_value=0.0, trend=t
            )
            assert c.trend == t


class TestForecastResponse:
    def test_from_attributes_enabled(self):
        assert ForecastResponse.model_config.get("from_attributes") is True

    def test_stores_all_required_fields(self):
        r = ForecastResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            domain="SCHEDULE",
            current_value=100.0,
            forecast_value=95.0,
            confidence=0.8,
            trend="DOWN",
        )
        assert r.domain == "SCHEDULE"
        assert r.trend == "DOWN"

    def test_computed_at_optional(self):
        r = ForecastResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            domain="BUDGET",
            current_value=0.0,
            forecast_value=0.0,
            confidence=0.5,
            trend="STABLE",
        )
        assert r.computed_at is None


class TestForecastSummaryResponse:
    def test_stores_project_id_and_domains(self):
        pid = uuid.uuid4()
        r = ForecastSummaryResponse(project_id=pid, domains=[], total=0)
        assert r.project_id == pid
        assert r.domains == []
        assert r.total == 0
