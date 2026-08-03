"""Tests for Monte Carlo domain schemas — S9-02."""
import pytest
from dataclasses import FrozenInstanceError

from app.monte_carlo.schemas import (
    MonteCarloInput,
    MonteCarloResult,
    PercentileResult,
    _DEFAULT_ITERATIONS,
)


class TestDefaultIterations:
    def test_default_is_ten_thousand(self):
        assert _DEFAULT_ITERATIONS == 10_000


class TestMonteCarloInput:
    def test_stores_base_schedule(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)
        assert mc.base_schedule == 100.0

    def test_stores_schedule_std_dev(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)
        assert mc.schedule_std_dev == 10.0

    def test_stores_base_cost(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)
        assert mc.base_cost == 500_000.0

    def test_stores_cost_std_dev(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)
        assert mc.cost_std_dev == 50_000.0

    def test_default_iterations(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)
        assert mc.iterations == 10_000

    def test_custom_iterations(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0, iterations=500)
        assert mc.iterations == 500

    def test_is_frozen(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)
        with pytest.raises(FrozenInstanceError):
            mc.base_schedule = 200.0  # type: ignore[misc]

    def test_zero_iterations_raises(self):
        with pytest.raises(ValueError, match="iterations"):
            MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0, iterations=0)

    def test_negative_iterations_raises(self):
        with pytest.raises(ValueError, match="iterations"):
            MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0, iterations=-1)

    def test_negative_schedule_std_dev_raises(self):
        with pytest.raises(ValueError, match="schedule_std_dev"):
            MonteCarloInput(base_schedule=100.0, schedule_std_dev=-1.0, base_cost=500_000.0, cost_std_dev=50_000.0)

    def test_negative_cost_std_dev_raises(self):
        with pytest.raises(ValueError, match="cost_std_dev"):
            MonteCarloInput(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=-1.0)

    def test_zero_std_devs_valid(self):
        mc = MonteCarloInput(base_schedule=100.0, schedule_std_dev=0.0, base_cost=500_000.0, cost_std_dev=0.0)
        assert mc.schedule_std_dev == 0.0
        assert mc.cost_std_dev == 0.0


class TestPercentileResult:
    def test_stores_p10(self):
        pr = PercentileResult(p10=10.0, p50=50.0, p80=80.0)
        assert pr.p10 == 10.0

    def test_stores_p50(self):
        pr = PercentileResult(p10=10.0, p50=50.0, p80=80.0)
        assert pr.p50 == 50.0

    def test_stores_p80(self):
        pr = PercentileResult(p10=10.0, p50=50.0, p80=80.0)
        assert pr.p80 == 80.0

    def test_is_frozen(self):
        pr = PercentileResult(p10=10.0, p50=50.0, p80=80.0)
        with pytest.raises(FrozenInstanceError):
            pr.p10 = 5.0  # type: ignore[misc]

    def test_equal_percentiles_valid(self):
        pr = PercentileResult(p10=50.0, p50=50.0, p80=50.0)
        assert pr.p10 == pr.p50 == pr.p80

    def test_p10_greater_than_p50_raises(self):
        with pytest.raises(ValueError, match="p10 <= p50 <= p80"):
            PercentileResult(p10=60.0, p50=50.0, p80=80.0)

    def test_p50_greater_than_p80_raises(self):
        with pytest.raises(ValueError, match="p10 <= p50 <= p80"):
            PercentileResult(p10=10.0, p50=90.0, p80=80.0)

    def test_as_dict_returns_three_keys(self):
        pr = PercentileResult(p10=10.0, p50=50.0, p80=80.0)
        d = pr.as_dict()
        assert set(d.keys()) == {"p10", "p50", "p80"}

    def test_as_dict_values_correct(self):
        pr = PercentileResult(p10=10.5, p50=50.5, p80=80.5)
        d = pr.as_dict()
        assert d["p10"] == 10.5 and d["p50"] == 50.5 and d["p80"] == 80.5


class TestMonteCarloResult:
    def _make(self) -> MonteCarloResult:
        schedule = PercentileResult(p10=90.0, p50=100.0, p80=115.0)
        cost = PercentileResult(p10=450_000.0, p50=500_000.0, p80=560_000.0)
        return MonteCarloResult(iterations=1000, schedule=schedule, cost=cost)

    def test_stores_iterations(self):
        assert self._make().iterations == 1000

    def test_stores_schedule(self):
        r = self._make()
        assert r.schedule.p50 == 100.0

    def test_stores_cost(self):
        r = self._make()
        assert r.cost.p50 == 500_000.0

    def test_is_frozen(self):
        r = self._make()
        with pytest.raises(FrozenInstanceError):
            r.iterations = 9999  # type: ignore[misc]

    def test_as_dict_has_three_top_keys(self):
        d = self._make().as_dict()
        assert set(d.keys()) == {"iterations", "schedule", "cost"}

    def test_as_dict_schedule_has_percentile_keys(self):
        d = self._make().as_dict()
        assert set(d["schedule"].keys()) == {"p10", "p50", "p80"}

    def test_as_dict_cost_has_percentile_keys(self):
        d = self._make().as_dict()
        assert set(d["cost"].keys()) == {"p10", "p50", "p80"}
