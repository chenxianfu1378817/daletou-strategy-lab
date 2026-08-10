from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .atomic import AtomicBet, portfolio_cost
from .prize import settle_portfolio
from .rules import LotteryRule


@dataclass(frozen=True)
class SimulationSummary:
    iterations: int
    horizon: int
    roi_p5: float
    roi_p25: float
    roi_p50: float
    roi_p75: float
    roi_p95: float
    profit_probability: float
    mean_roi: float
    extreme_loss_probability: float


class PrizeScenarioEngine:
    """Only consumes prize observations available before the simulated target."""

    def __init__(self, first_prizes: Sequence[int], second_prizes: Sequence[int]):
        if not first_prizes or not second_prizes:
            raise ValueError("Prize scenarios require historical first and second prize observations")
        self.first_prizes = tuple(int(value) for value in first_prizes if value > 0)
        self.second_prizes = tuple(int(value) for value in second_prizes if value > 0)

    def sample(self, generator: random.Random, fixed: Mapping[int, int]) -> Dict[int, int]:
        result = dict(fixed)
        result[1] = generator.choice(self.first_prizes)
        result[2] = generator.choice(self.second_prizes)
        return result


def _percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def uniform_draw(rule: LotteryRule, generator: random.Random) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    front = tuple(sorted(generator.sample(range(1, rule.front_pool + 1), rule.front_pick)))
    back = tuple(sorted(generator.sample(range(1, rule.back_pool + 1), rule.back_pick)))
    return front, back


def monte_carlo(
    portfolio: Sequence[AtomicBet],
    rule: LotteryRule,
    iterations: int = 10000,
    horizon: int = 100,
    seed: int = 0,
    prize_scenarios: PrizeScenarioEngine = None,
) -> SimulationSummary:
    if iterations < 1 or horizon < 1:
        raise ValueError("iterations和horizon必须为正数")
    generator = random.Random(seed)
    cost_per_period = portfolio_cost(portfolio, rule)
    fixed_payouts = {level.level: level.amount for level in rule.prize_levels if level.amount is not None}
    scenarios = prize_scenarios or PrizeScenarioEngine([5_000_000], [100_000])
    rois = []
    for _ in range(iterations):
        total_prize = 0
        for _period in range(horizon):
            front, back = uniform_draw(rule, generator)
            payouts = scenarios.sample(generator, fixed_payouts)
            settled = settle_portfolio(portfolio, front, back, rule, __import__("datetime").date.today(), payouts)
            total_prize += int(settled["net_prize"])
        total_cost = cost_per_period * horizon
        rois.append((total_prize - total_cost) / total_cost if total_cost else 0.0)
    return SimulationSummary(
        iterations=iterations,
        horizon=horizon,
        roi_p5=_percentile(rois, 0.05),
        roi_p25=_percentile(rois, 0.25),
        roi_p50=_percentile(rois, 0.5),
        roi_p75=_percentile(rois, 0.75),
        roi_p95=_percentile(rois, 0.95),
        profit_probability=sum(value > 0 for value in rois) / len(rois),
        mean_roi=mean(rois),
        extreme_loss_probability=sum(value <= -0.8 for value in rois) / len(rois),
    )


def historical_bootstrap(period_profits: Sequence[int], periods: int, iterations: int = 1000, seed: int = 0) -> List[int]:
    if not period_profits:
        return []
    generator = random.Random(seed)
    return [sum(generator.choice(period_profits) for _ in range(periods)) for _ in range(iterations)]
