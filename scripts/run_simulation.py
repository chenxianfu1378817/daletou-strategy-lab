#!/usr/bin/env python3
import argparse
import json
from dataclasses import asdict

from daletou_lab.atomic import AtomicBet
from daletou_lab.rules import RuleRegistry
from daletou_lab.simulation import monte_carlo


def main() -> None:
    parser = argparse.ArgumentParser(description="Uniform-draw Monte Carlo with correlated portfolio settlement")
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--horizon", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260810)
    args = parser.parse_args()
    portfolio = [AtomicBet((3, 11, 18, 24, 33), (4, 9))]
    summary = monte_carlo(portfolio, RuleRegistry().current(), args.iterations, args.horizon, args.seed)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

