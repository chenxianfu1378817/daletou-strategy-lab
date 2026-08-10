#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from daletou_lab.atomic import AtomicBet
from daletou_lab.database import connect, initialize, realized_prizes
from daletou_lab.prize import settle_portfolio
from daletou_lab.rules import RuleRegistry


def parse_atomic(text: str) -> AtomicBet:
    front_text, back_text = text.split("+")
    return AtomicBet(tuple(map(int, front_text.split())), tuple(map(int, back_text.split())))


def main() -> None:
    parser = argparse.ArgumentParser(description="Settle immutable paper bets only after verified draws exist")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    args = parser.parse_args()
    initialize(args.db)
    registry = RuleRegistry()
    settled_count = 0
    with connect(args.db) as connection:
        rows = connection.execute(
            """SELECT pb.id,pb.payload_json,d.* FROM paper_bets pb
            JOIN predictions p ON p.prediction_id=pb.prediction_id
            JOIN draws d ON d.issue=p.issue AND d.verified=1
            WHERE pb.settled_at IS NULL ORDER BY pb.id"""
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            atoms = [parse_atomic(text) for text in payload.get("numbers", [])]
            rule = registry.for_issue(row["issue"])
            result = settle_portfolio(
                atoms,
                tuple(row[f"front_{index}"] for index in range(1, 6)),
                tuple(row[f"back_{index}"] for index in range(1, 3)),
                rule,
                date.fromisoformat(row["draw_date"]),
                realized_prizes(connection, row["issue"]),
                row["jackpot_before"],
            )
            cost = int(payload.get("cost", 0))
            connection.execute(
                "UPDATE paper_bets SET settled_at=?,gross_prize=?,net_profit=? WHERE id=? AND settled_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), int(result["gross_prize"]), int(result["net_prize"]) - cost, row["id"]),
            )
            settled_count += 1
    print(json.dumps({"settled": settled_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
