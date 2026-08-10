#!/usr/bin/env python3
import argparse
from pathlib import Path

from daletou_lab.backtest import HoldoutLock


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-register a future locked holdout range")
    parser.add_argument("holdout_id")
    parser.add_argument("start_issue")
    parser.add_argument("end_issue")
    parser.add_argument("--model-version", default="Ensemble_v1")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    args = parser.parse_args()
    HoldoutLock(args.db).lock(args.holdout_id, args.start_issue, args.end_issue, args.model_version)
    print(f"locked {args.holdout_id}: {args.start_issue}-{args.end_issue} for {args.model_version}")


if __name__ == "__main__":
    main()

