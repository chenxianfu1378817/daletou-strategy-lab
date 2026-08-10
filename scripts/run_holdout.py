#!/usr/bin/env python3
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from daletou_lab.backtest import HoldoutLock, WalkForwardBacktester, summarize
from daletou_lab.database import load_draws
from daletou_lab.models import MODEL_REGISTRY


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a pre-locked holdout exactly once")
    parser.add_argument("holdout_id")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    parser.add_argument("--model", default="Ensemble")
    parser.add_argument("--budget", type=int, default=20)
    args = parser.parse_args()
    draws = load_draws(args.db)
    tester = WalkForwardBacktester(draws, args.db)
    result = summarize(args.model, args.holdout_id, tester.run(MODEL_REGISTRY[args.model], args.budget))
    payload = asdict(result)
    HoldoutLock(args.db).evaluate_once(args.holdout_id, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

