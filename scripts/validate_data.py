#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from daletou_lab.database import load_draws
from daletou_lab.validation import validate_draws


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the local history database")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    args = parser.parse_args()
    draws = load_draws(args.db)
    warnings = validate_draws(draws)
    print(json.dumps({"draws": len(draws), "warnings": [item.__dict__ for item in warnings]}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if warnings else 0)


if __name__ == "__main__":
    main()

