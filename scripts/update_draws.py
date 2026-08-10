#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from daletou_lab.source import update_official


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally update official Super Lotto history")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    args = parser.parse_args()
    print(json.dumps(update_official(args.db), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

