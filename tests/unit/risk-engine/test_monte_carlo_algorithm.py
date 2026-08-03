"""Tests for Monte Carlo simulation algorithm — S9-02."""
import pytest

from app.monte_carlo.algorithm import run_monte_carlo
from app.monte_carlo.schemas import MonteCarloInput, MonteCarloResult, PercentileResult

_BASE = dict(base_schedule=100.0, schedule_std_dev=10.0, base_cost=500_000.0, cost_std_dev=50_000.0)


def _small(**overrides) -> MonteCarloInput:
    """Low-iteration input for fast tests."""
    return MonteCarloInput(**{**_BASE, "iterations": 200, **overrides})


class TestRunMonteCarloReturnType:
    def test_returns_monte_carlo_result(self):
        result = run_monte_carlo(_small(), seed=0)
        assert isinstance(result, MonteCarloResult)

    def test_schedule_is_percentile_result(self):
        result = run_monte_carlo(_small(), seed=0)
        assert isinstance(result.schedule, PercentileResult)

    def test_cost_is_percentile_result(self):
        result = run_monte_carlo(_small(), seed=0)
        assert isinstance(result.cost, PercentileResult)

    def test_iterations_stored(self):
        result = run_monte_carlo(_small(iterations=50), seed=0)
        assert result.iterations == 50


class TestDeterminism:
    def test_same_seed_produces_same_result(self):
        r1 = run_monte_carlo(_small(), seed=42)
        r2 = run_monte_carlo(_small(), seed=42)
        assert r1.schedule.p50 == r2.schedule.p50
        assert r1.cost.p50 == r2.cost.p50

    def test_different_seeds_likely_differ(self):
        r1 = run_monte_carlo(_small(iterations=1000), seed=1)
        r2 = run_monte_carlo(_small(iterations=1000), seed=2)
        # With 1000 samples and non-trivial std_dev, p50s will differ
        assert r1.schedule.p50 != r2.schedule.p50

    def test_no_seed_produces_result(self):
        result = run_monte_carlo(_small())
        assert result.schedule.p50 > 0


class TestPercentileOrdering:
    def test_schedule_p10_le_p50(self):
        result = run_monte_carlo(_small(iterations=500), seed=7)
        assert result.schedule.p10 <= result.schedule.p50

    def test_schedule_p50_le_p80(self):
        result = run_monte_carlo(_small(iterations=500), seed=7)
        assert result.schedule.p50 <= result.schedule.p80

    def test_cost_p10_le_p50(self):
        result = run_monte_carlo(_small(iterations=500), seed=7)
        assert result.cost.p10 <= result.cost.p50

    def test_cost_p50_le_p80(self):
        result = run_monte_carlo(_small(iterations=500), seed=7)
        assert result.cost.p50 <= result.cost.p80

    def test_p10_strictly_less_than_p80_nonzero_stddev(self):
        result = run_monte_carlo(_small(iterations=1000), seed=3)
        assert result.schedule.p10 < result.schedule.p80


class TestZeroStdDev:
    def test_schedule_p10_equals_base_when_zero_stddev(self):
        mc = _small(schedule_std_dev=0.0, iterations=100)
        result = run_monte_carlo(mc, seed=0)
        assert result.schedule.p10 == pytest.approx(100.0)

    def test_schedule_p50_equals_base_when_zero_stddev(self):
        mc = _small(schedule_std_dev=0.0, iterations=100)
        result = run_monte_carlo(mc, seed=0)
        assert result.schedule.p50 == pytest.approx(100.0)

    def test_schedule_p80_equals_base_when_zero_stddev(self):
        mc = _small(schedule_std_dev=0.0, iterations=100)
        result = run_monte_carlo(mc, seed=0)
        assert result.schedule.p80 == pytest.approx(100.0)

    def test_cost_equal_percentiles_when_zero_stddev(self):
        mc = _small(cost_std_dev=0.0, iterations=100)
        result = run_monte_carlo(mc, seed=0)
        assert result.cost.p10 == result.cost.p50 == result.cost.p80


class TestRounding:
    def test_schedule_p50_is_rounded_to_2dp(self):
        result = run_monte_carlo(_small(), seed=5)
        p50 = result.schedule.p50
        assert round(p50, 2) == p50

    def test_cost_p80_is_rounded_to_2dp(self):
        result = run_monte_carlo(_small(), seed=5)
        p80 = result.cost.p80
        assert round(p80, 2) == p80


class TestCentering:
    def test_p50_close_to_base_schedule_large_iterations(self):
        mc = MonteCarloInput(
            base_schedule=100.0, schedule_std_dev=5.0,
            base_cost=500_000.0, cost_std_dev=25_000.0,
            iterations=10_000,
        )
        result = run_monte_carlo(mc, seed=0)
        assert abs(result.schedule.p50 - 100.0) < 2.0

    def test_p50_close_to_base_cost_large_iterations(self):
        mc = MonteCarloInput(
            base_schedule=100.0, schedule_std_dev=5.0,
            base_cost=500_000.0, cost_std_dev=25_000.0,
            iterations=10_000,
        )
        result = run_monte_carlo(mc, seed=0)
        assert abs(result.cost.p50 - 500_000.0) < 5_000.0
