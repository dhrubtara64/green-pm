"""Monte Carlo simulation algorithm — S9-02.

Runs N iterations sampling schedule and cost from Gaussian distributions
and returns P10 / P50 / P80 percentiles for each dimension.
"""
from __future__ import annotations

import random

from app.monte_carlo.schemas import MonteCarloInput, MonteCarloResult, PercentileResult


def _percentile(sorted_data: list[float], p: float) -> float:
    """Return the p-th percentile of pre-sorted data (p in [0, 100])."""
    n = len(sorted_data)
    idx = min(int(n * p / 100), n - 1)
    return sorted_data[idx]


def run_monte_carlo(
    mc_input: MonteCarloInput,
    seed: int | None = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulation and return P10/P50/P80 for schedule and cost.

    Args:
        mc_input: Simulation parameters (base values, std devs, iterations).
        seed: Optional RNG seed for deterministic output (used in tests).

    Returns:
        MonteCarloResult with percentile distributions for schedule and cost.
    """
    rng = random.Random(seed)

    schedule_samples: list[float] = [
        rng.gauss(mc_input.base_schedule, mc_input.schedule_std_dev)
        for _ in range(mc_input.iterations)
    ]
    cost_samples: list[float] = [
        rng.gauss(mc_input.base_cost, mc_input.cost_std_dev)
        for _ in range(mc_input.iterations)
    ]

    schedule_sorted = sorted(schedule_samples)
    cost_sorted = sorted(cost_samples)

    return MonteCarloResult(
        iterations=mc_input.iterations,
        schedule=PercentileResult(
            p10=round(_percentile(schedule_sorted, 10), 2),
            p50=round(_percentile(schedule_sorted, 50), 2),
            p80=round(_percentile(schedule_sorted, 80), 2),
        ),
        cost=PercentileResult(
            p10=round(_percentile(cost_sorted, 10), 2),
            p50=round(_percentile(cost_sorted, 50), 2),
            p80=round(_percentile(cost_sorted, 80), 2),
        ),
    )
