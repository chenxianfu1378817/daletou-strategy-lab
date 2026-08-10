#!/usr/bin/env python3
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from daletou_lab.backtest import WalkForwardBacktester, random_distribution, summarize
from daletou_lab.database import load_draws
from daletou_lab.models import MODEL_REGISTRY


def main() -> None:
    parser = argparse.ArgumentParser(description="Run leakage-safe walk-forward backtests")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    parser.add_argument("--budget", type=int, default=20)
    parser.add_argument("--window", type=int, default=300)
    parser.add_argument("--random-seeds", type=int, default=100)
    parser.add_argument("--models", nargs="+", default=["Random", "RandomCoverage", "Frequency", "Bayesian", "Ensemble"])
    parser.add_argument("--out", type=Path, default=Path("data/exports/backtest.json"))
    args = parser.parse_args()
    draws = load_draws(args.db, limit=max(args.window + 120, 200))
    backtester = WalkForwardBacktester(draws, args.db, min_history=min(120, max(30, len(draws) // 4)))
    random_rois = random_distribution(backtester, args.budget, args.random_seeds)
    baseline_roi = sum(random_rois) / len(random_rois) if random_rois else 0.0
    output = []
    for name in args.models:
        model_name = "Random" if name == "RandomCoverage" else name
        model = MODEL_REGISTRY[model_name]
        results = backtester.run(model, budget=args.budget, seed=42, optimize_coverage=name != "Random")
        metrics = summarize(name, f"最近{min(args.window, len(results))}期", results[-args.window :], random_rois, baseline_roi)
        output.append(asdict(metrics))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
