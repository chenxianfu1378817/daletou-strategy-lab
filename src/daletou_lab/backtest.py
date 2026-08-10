from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .atomic import AtomicBet, portfolio_cost
from .database import DEFAULT_DB, Draw, connect, realized_prizes
from .models import MODEL_REGISTRY, NumberModel, RandomModel
from .optimizer import greedy_coverage
from .prize import settle_portfolio
from .rules import RuleRegistry


@dataclass(frozen=True)
class PeriodResult:
    issue: str
    cost: int
    gross_prize: int
    net_prize: int
    net_profit: int
    highest_prize: int


@dataclass(frozen=True)
class BacktestMetrics:
    model: str
    period: str
    tickets: int
    bet_periods: int
    skip_periods: int
    total_cost: int
    total_prize: int
    net_profit: int
    roi: float
    excess_roi: float
    max_drawdown: int
    profit_factor: float
    profitable_draw_rate: float
    longest_losing_streak: int
    largest_prize: int
    roi_excluding_largest: float
    roi_excluding_top_1pct: float
    non_jackpot_roi: float
    random_percentile: float


def _maximum_drawdown(profits: Sequence[int]) -> int:
    equity = peak = 0
    maximum = 0
    for profit in profits:
        equity += profit
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _longest_losing_streak(profits: Sequence[int]) -> int:
    longest = current = 0
    for profit in profits:
        if profit < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def summarize(model: str, period: str, results: Sequence[PeriodResult], random_rois: Sequence[float] = (), baseline_roi: float = 0.0) -> BacktestMetrics:
    costs = sum(row.cost for row in results)
    prizes = sum(row.net_prize for row in results)
    profits = [row.net_profit for row in results]
    roi = (prizes - costs) / costs if costs else 0.0
    positive = sum(value for value in profits if value > 0)
    negative = abs(sum(value for value in profits if value < 0))
    ordered_prizes = sorted((row.net_prize for row in results), reverse=True)
    largest = ordered_prizes[0] if ordered_prizes else 0
    excluded_cost = costs
    roi_no_largest = (prizes - largest - excluded_cost) / excluded_cost if excluded_cost else 0.0
    top_count = max(1, math.ceil(len(ordered_prizes) * 0.01)) if ordered_prizes else 0
    roi_no_top = (prizes - sum(ordered_prizes[:top_count]) - costs) / costs if costs else 0.0
    random_percentile = sum(value <= roi for value in random_rois) / len(random_rois) if random_rois else 0.5
    return BacktestMetrics(
        model=model,
        period=period,
        tickets=sum(row.cost // 2 for row in results),
        bet_periods=sum(row.cost > 0 for row in results),
        skip_periods=sum(row.cost == 0 for row in results),
        total_cost=costs,
        total_prize=prizes,
        net_profit=prizes - costs,
        roi=roi,
        excess_roi=roi - baseline_roi,
        max_drawdown=_maximum_drawdown(profits),
        profit_factor=positive / negative if negative else float("inf") if positive else 0.0,
        profitable_draw_rate=sum(value > 0 for value in profits) / len(profits) if profits else 0.0,
        longest_losing_streak=_longest_losing_streak(profits),
        largest_prize=largest,
        roi_excluding_largest=roi_no_largest,
        roi_excluding_top_1pct=roi_no_top,
        non_jackpot_roi=roi_no_largest,
        random_percentile=random_percentile,
    )


class WalkForwardBacktester:
    def __init__(self, draws: Sequence[Draw], db_path: Path = DEFAULT_DB, min_history: int = 120):
        self.draws = tuple(sorted(draws, key=lambda draw: int(draw.issue)))
        self.db_path = db_path
        self.min_history = min_history
        self.registry = RuleRegistry()

    def run(self, model: NumberModel, budget: int = 20, start_index: Optional[int] = None, seed: int = 0, optimize_coverage: bool = True) -> List[PeriodResult]:
        if not 0 <= budget <= 100:
            raise ValueError("预算必须在0到100元之间")
        start = max(self.min_history, start_index or self.min_history)
        output = []
        with connect(self.db_path) as connection:
            for index in range(start, len(self.draws)):
                target = self.draws[index]
                history = self.draws[:index]
                if any(int(draw.issue) >= int(target.issue) for draw in history):
                    raise RuntimeError("Leakage detected: history contains target or future issue")
                rule = self.registry.for_issue(target.issue)
                scores = model.score(history, rule, seed + index)
                atomic_count = budget // rule.base_price
                if isinstance(model, RandomModel) and not optimize_coverage:
                    generator = random.Random(seed + index)
                    atoms = []
                    seen = set()
                    while len(atoms) < atomic_count:
                        bet = AtomicBet(
                            tuple(sorted(generator.sample(range(1, rule.front_pool + 1), rule.front_pick))),
                            tuple(sorted(generator.sample(range(1, rule.back_pool + 1), rule.back_pick))),
                        )
                        if bet not in seen:
                            seen.add(bet)
                            atoms.append(bet)
                else:
                    atoms = greedy_coverage(scores, rule, atomic_count, seed + index)
                cost = portfolio_cost(atoms, rule)
                payouts = realized_prizes(connection, target.issue)
                settled = settle_portfolio(
                    atoms,
                    target.front,
                    target.back,
                    rule,
                    date.fromisoformat(target.draw_date),
                    payouts,
                    target.jackpot_before,
                )
                output.append(
                    PeriodResult(
                        issue=target.issue,
                        cost=cost,
                        gross_prize=int(settled["gross_prize"]),
                        net_prize=int(settled["net_prize"]),
                        net_profit=int(settled["net_prize"]) - cost,
                        highest_prize=max((row.gross_prize for row in settled["results"]), default=0),
                    )
                )
        return output


def random_distribution(backtester: WalkForwardBacktester, budget: int, seeds: int = 100) -> List[float]:
    values = []
    for seed in range(seeds):
        results = backtester.run(RandomModel(), budget=budget, seed=seed * 10007, optimize_coverage=False)
        values.append(summarize("Random", "baseline", results).roi)
    return values


class HoldoutLock:
    def __init__(self, db_path: Path = DEFAULT_DB):
        self.db_path = db_path

    def lock(self, holdout_id: str, start_issue: str, end_issue: str, model_version: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO holdout_registry(holdout_id,start_issue,end_issue,model_version,locked_at) VALUES(?,?,?,?,?)",
                (holdout_id, start_issue, end_issue, model_version, datetime.now(timezone.utc).isoformat()),
            )

    def evaluate_once(self, holdout_id: str, result: Mapping[str, object]) -> None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT evaluated_at FROM holdout_registry WHERE holdout_id=?", (holdout_id,)).fetchone()
            if row is None:
                raise LookupError("Holdout未预先锁定")
            if row[0] is not None:
                raise RuntimeError("Holdout只能验收一次")
            connection.execute(
                "UPDATE holdout_registry SET evaluated_at=?,result_json=? WHERE holdout_id=?",
                (datetime.now(timezone.utc).isoformat(), json.dumps(result, ensure_ascii=False), holdout_id),
            )
