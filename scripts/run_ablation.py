#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from daletou_lab.atomic import AtomicBet, portfolio_cost
from daletou_lab.backtest import PeriodResult, summarize
from daletou_lab.database import connect, load_draws
from daletou_lab.models import EnsembleModel, RandomModel
from daletou_lab.optimizer import build_plan, greedy_coverage, signal_ranked
from daletou_lab.prize import settle_portfolio, tax_for_issue
from daletou_lab.rules import RuleRegistry
from daletou_lab.simulation import historical_bootstrap


WINDOWS = (100, 300, 500)
MODES = (("单式", "Single"), ("复式", "Multiple"), ("混合", "Hybrid"))
BUDGETS = (20, 30, 40, 50, 60, 70, 80, 90, 100)


def load_payouts(db_path: Path) -> dict[str, dict[int, int]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT issue,prize_level,prize_per_ticket FROM prizes WHERE additional=0 AND prize_per_ticket IS NOT NULL"
        ).fetchall()
    result: dict[str, dict[int, int]] = {}
    for row in rows:
        result.setdefault(str(row[0]), {})[int(row[1])] = int(row[2])
    return result


def settle_atoms(atoms, target, rule, payouts) -> PeriodResult:
    cost = portfolio_cost(atoms, rule)
    settled = settle_portfolio(
        atoms, target.front, target.back, rule, date.fromisoformat(target.draw_date),
        payouts.get(target.issue, {}), target.jackpot_before,
    )
    return PeriodResult(
        target.issue, cost, int(settled["gross_prize"]), int(settled["net_prize"]),
        int(settled["net_prize"]) - cost,
        max((row.gross_prize for row in settled["results"]), default=0),
    )


def fast_random_period(target, rule, payouts, budget: int, seed: int) -> PeriodResult:
    generator = random.Random(seed)
    atomic_count = budget // rule.base_price
    winning_front, winning_back = set(target.front), set(target.back)
    seen = set()
    gross = highest = 0
    while len(seen) < atomic_count:
        front = tuple(sorted(generator.sample(range(1, rule.front_pool + 1), rule.front_pick)))
        back = tuple(sorted(generator.sample(range(1, rule.back_pool + 1), rule.back_pick)))
        key = (front, back)
        if key in seen:
            continue
        seen.add(key)
        level = rule.prize_level_for(len(set(front) & winning_front), len(set(back) & winning_back))
        if level is None:
            prize = 0
        elif level.level in payouts.get(target.issue, {}):
            prize = payouts[target.issue][level.level]
        elif level.amount is not None:
            high_pool = bool(
                rule.high_pool_threshold is not None and target.jackpot_before is not None
                and target.jackpot_before >= rule.high_pool_threshold
            )
            prize = int(level.high_pool_amount if high_pool and level.high_pool_amount is not None else level.amount)
        else:
            raise ValueError(f"{target.issue}缺少官方浮动奖金")
        gross += prize
        highest = max(highest, prize)
    cost = atomic_count * rule.base_price
    net = gross - tax_for_issue(gross, date.fromisoformat(target.draw_date))
    return PeriodResult(target.issue, cost, gross, net, net - cost, highest)


def metric_dict(name, window, results, random_rois, baseline_roi):
    return asdict(summarize(name, f"最近{window}期", results[-window:], random_rois, baseline_roi))


def random_summary(trajectories, window):
    metrics = [asdict(summarize("Random", f"最近{window}期", rows[-window:])) for rows in trajectories]
    numeric = (
        "tickets", "total_cost", "total_prize", "net_profit", "roi", "max_drawdown",
        "profit_factor", "profitable_draw_rate", "longest_losing_streak", "largest_prize",
        "roi_excluding_largest", "roi_excluding_top_1pct", "non_jackpot_roi",
    )
    result = {
        "model": "Random", "period": f"最近{window}期", "random_seeds": len(trajectories),
        "random_percentile": 0.5, "bet_periods": window, "skip_periods": 0,
    }
    for key in numeric:
        result[key] = mean(float(row[key]) for row in metrics)
    result["excess_roi"] = 0.0
    return result


def candidate_metric(results, random_rois, baseline_roi, budget, mode, seed):
    metrics = metric_dict(mode, 500, results, random_rois, baseline_roi)
    bootstraps = historical_bootstrap([row.net_profit for row in results[-500:]], 100, iterations=2000, seed=seed)
    return {
        "historical_oos_roi": metrics["roi"],
        "excess_roi_vs_random": metrics["excess_roi"],
        "random_percentile": metrics["random_percentile"],
        "maximum_drawdown": metrics["max_drawdown"],
        "maximum_drawdown_ratio": metrics["max_drawdown"] / metrics["total_cost"] if metrics["total_cost"] else 1.0,
        "roi_excluding_largest_win": metrics["roi_excluding_largest"],
        "monte_carlo_profit_probability": sum(value > 0 for value in bootstraps) / len(bootstraps),
        "monte_carlo_iterations": len(bootstraps),
        "monte_carlo_horizon": 100,
        "jackpot_sensitivity": abs(metrics["roi"] - metrics["roi_excluding_largest"]),
        "tested_budget": budget,
        "tested_periods": len(results[-500:]),
        "method": "leakage-safe walk-forward + historical Monte Carlo bootstrap",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V1.1.0 strict ablation and candidate comparisons")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    parser.add_argument("--random-seeds", type=int, default=1000)
    parser.add_argument("--out", type=Path, default=Path("data/exports/ablation-v1.1.0.json"))
    args = parser.parse_args()
    if args.random_seeds < 1000:
        raise SystemExit("Formal V1.1.0 comparison requires at least 1000 random seeds")
    draws = load_draws(args.db, limit=620)
    if len(draws) < 620:
        raise SystemExit("At least 620 verified draws are required")
    registry, payouts = RuleRegistry(), load_payouts(args.db)
    targets = draws[-500:]

    random_trajectories = []
    for random_seed in range(args.random_seeds):
        rows = []
        for offset, target in enumerate(targets):
            rule = registry.for_issue(target.issue)
            rows.append(fast_random_period(target, rule, payouts, 20, random_seed * 10007 + offset + 120))
        random_trajectories.append(rows)
    random_rois = {
        window: [summarize("Random", str(window), rows[-window:]).roi for rows in random_trajectories]
        for window in WINDOWS
    }
    baseline_rois = {window: mean(values) for window, values in random_rois.items()}

    random_coverage: list[PeriodResult] = []
    current_model: list[PeriodResult] = []
    current_coverage: list[PeriodResult] = []
    candidate_rows = {str(budget): {key: [] for _, key in MODES} for budget in BUDGETS}
    ensemble = EnsembleModel()
    for absolute_index, target in enumerate(targets, start=len(draws) - len(targets)):
        history = draws[:absolute_index]
        rule = registry.for_issue(target.issue)
        scores = ensemble.score(history, rule, seed=42 + absolute_index)
        random_scores = RandomModel().score(history, rule, seed=42 + absolute_index)
        random_coverage.append(settle_atoms(greedy_coverage(random_scores, rule, 10, 42 + absolute_index), target, rule, payouts))
        signal_bets = signal_ranked(scores, rule, 50, 42 + absolute_index)
        coverage_bets = greedy_coverage(scores, rule, 50, 42 + absolute_index)
        current_model.append(settle_atoms(signal_bets[:10], target, rule, payouts))
        current_coverage.append(settle_atoms(coverage_bets[:10], target, rule, payouts))
        for budget in BUDGETS:
            for chinese_mode, mode_key in MODES:
                plan = build_plan(scores, rule, budget, chinese_mode, 42 + absolute_index, coverage_bets)
                candidate_rows[str(budget)][mode_key].append(settle_atoms(plan.atomic_bets, target, rule, payouts))

    ablation = {}
    for window in WINDOWS:
        baseline = baseline_rois[window]
        rows = [
            random_summary(random_trajectories, window),
            metric_dict("Random + Coverage", window, random_coverage, random_rois[window], baseline),
            metric_dict("Current Model", window, current_model, random_rois[window], baseline),
            metric_dict("Current Model + Coverage", window, current_coverage, random_rois[window], baseline),
        ]
        for name in (
            "Current Model + Coverage + Bet/Skip",
            "Current Model + Coverage + Bet/Skip + Budget/Smart",
        ):
            zero = metric_dict(name, window, [PeriodResult(row.issue, 0, 0, 0, 0, 0) for row in current_coverage], random_rois[window], baseline)
            zero["excess_roi"] = 0.0
            zero["random_percentile"] = 0.5
            zero["investment_metrics_applicable"] = False
            zero["not_applicable_reason"] = "No eligible saved Evidence; strict gate skipped every period"
            rows.append(zero)
        ablation[str(window)] = rows

    candidates = {}
    for budget in BUDGETS:
        candidates[str(budget)] = {}
        for _, mode_key in MODES:
            candidates[str(budget)][mode_key] = candidate_metric(
                candidate_rows[str(budget)][mode_key], random_rois[500], baseline_rois[500], budget, mode_key,
                budget * 1000 + len(mode_key),
            )
    excesses = [next(row["excess_roi"] for row in ablation[str(window)] if row["model"] == "Current Model + Coverage") for window in WINDOWS]
    payload = {
        "version": "1.1.0",
        "strategy_version": "V1.1.0",
        "model_version": "Ensemble_v1",
        "source_issue": draws[-1].issue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "random_seed_count": args.random_seeds,
        "random_distribution": {
            str(window): {
                "mean_roi": baseline_rois[window],
                "median_roi": sorted(random_rois[window])[len(random_rois[window]) // 2],
                "p05_roi": sorted(random_rois[window])[int(args.random_seeds * 0.05)],
                "p95_roi": sorted(random_rois[window])[min(args.random_seeds - 1, int(args.random_seeds * 0.95))],
            } for window in WINDOWS
        },
        "ablation": ablation,
        "candidate_backtests": candidates,
        "model_stability": (
            (sum(value > 0 for value in excesses) / len(excesses))
            * max(0.0, 1.0 - pstdev(excesses))
        ) if len(excesses) > 1 else 0.0,
        "notes": [
            "All targets use only draws strictly before that target.",
            "Locked Holdout interval was not changed or re-selected.",
            "Zero-cost gate rows are N/A investment returns, not evidence of profit.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(args.out)
    print(json.dumps({"output": str(args.out), "random_seeds": args.random_seeds, "source_issue": draws[-1].issue}, ensure_ascii=False))


if __name__ == "__main__":
    main()
