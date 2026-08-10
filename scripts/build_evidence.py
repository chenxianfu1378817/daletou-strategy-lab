#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from daletou_lab.database import connect, load_draws
from daletou_lab.evidence import MIN_FORWARD_PERIODS, save_evidence
from daletou_lab.validation import validate_draws


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fail-closed Evidence from saved backtest and Forward records")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    parser.add_argument("--ablation", type=Path, default=Path("data/exports/ablation-v1.1.0.json"))
    parser.add_argument("--out", type=Path, default=Path("data/exports/evidence.json"))
    args = parser.parse_args()
    draws = load_draws(args.db)
    if not draws:
        raise SystemExit("No verified draws")
    if not args.ablation.exists():
        raise SystemExit("Saved ablation is required; Evidence cannot be fabricated")
    ablation = json.loads(args.ablation.read_text(encoding="utf-8"))
    if str(ablation.get("source_issue")) != draws[-1].issue:
        raise SystemExit("Saved ablation is stale; refusing to build current Evidence")
    warnings = validate_draws(draws)
    with connect(args.db) as connection:
        holdout = connection.execute(
            "SELECT * FROM holdout_registry ORDER BY locked_at DESC LIMIT 1"
        ).fetchone()
        forward = connection.execute(
            "SELECT COUNT(*) AS periods, COALESCE(SUM(json_extract(payload_json,'$.cost')),0) AS cost, "
            "COALESCE(SUM(gross_prize),0) AS prize, COALESCE(SUM(net_profit),0) AS profit "
            "FROM paper_bets WHERE settled_at IS NOT NULL"
        ).fetchone()
    if holdout is None:
        holdout_payload = {"status": "MISSING"}
    elif holdout["evaluated_at"] is None:
        holdout_payload = {
            "status": "LOCKED_UNEVALUATED", "holdout_id": holdout["holdout_id"],
            "start_issue": holdout["start_issue"], "end_issue": holdout["end_issue"],
            "locked_at": holdout["locked_at"],
        }
    else:
        result = json.loads(holdout["result_json"])
        passed = bool(result.get("passed"))
        holdout_payload = {
            "status": "EVALUATED_PASS" if passed else "EVALUATED_FAIL",
            "holdout_id": holdout["holdout_id"], "start_issue": holdout["start_issue"],
            "end_issue": holdout["end_issue"], "evaluated_at": holdout["evaluated_at"], "result": result,
        }
    periods, cost, prize = int(forward["periods"]), int(forward["cost"]), int(forward["prize"])
    forward_roi = (prize - cost) / cost if cost else None
    forward_payload = {
        "status": "COMPLETE" if periods >= MIN_FORWARD_PERIODS else "INSUFFICIENT",
        "settled_periods": periods, "total_cost": cost, "total_prize": prize,
        "net_profit": int(forward["profit"]), "roi": forward_roi,
        "minimum_required_periods": MIN_FORWARD_PERIODS,
    }
    walk_forward = {}
    for window in (100, 300, 500):
        rows = ablation["ablation"][str(window)]
        current = next(row for row in rows if row["model"] == "Current Model + Coverage")
        walk_forward[str(window)] = {
            key: current[key] for key in (
                "roi", "excess_roi", "random_percentile", "max_drawdown", "roi_excluding_largest",
                "total_cost", "total_prize", "bet_periods",
            )
        }
    primary = walk_forward["500"]
    validation_payload = {
        "status": "PASS" if not warnings else "FAIL",
        "warning_count": len(warnings),
        "warnings": [warning.__dict__ for warning in warnings],
    }
    bet_eligible = bool(
        validation_payload["status"] == "PASS"
        and holdout_payload["status"] == "EVALUATED_PASS"
        and forward_payload["status"] == "COMPLETE"
        and isinstance(forward_roi, (int, float)) and forward_roi > 0
        and primary["roi"] > 0 and primary["excess_roi"] > 0
        and primary["random_percentile"] >= 0.95
        and primary["roi_excluding_largest"] > 0
        and ablation["model_stability"] >= 0.67
    )
    payload = {
        "schema_version": "evidence-v1.1",
        "strategy_version": "V1.1.0",
        "model_version": "Ensemble_v1",
        "source_issue": draws[-1].issue,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "VALID" if bet_eligible else ("INVALID" if warnings else "INSUFFICIENT"),
        "bet_eligible": bet_eligible,
        "random_seed_count": int(ablation["random_seed_count"]),
        "walk_forward": walk_forward,
        "random_distribution": ablation["random_distribution"],
        "validation": validation_payload,
        "holdout": holdout_payload,
        "forward_paper": forward_payload,
        "model_stability": ablation["model_stability"],
        "candidate_backtests": ablation["candidate_backtests"],
        "eligibility_rule": {
            "all_windows_saved": True, "random_seeds_minimum": 1000,
            "holdout_must_pass": True, "forward_periods_minimum": MIN_FORWARD_PERIODS,
            "positive_primary_roi": True, "positive_excess_roi": True,
            "random_percentile_minimum": 0.95, "positive_roi_excluding_largest": True,
            "model_stability_minimum": 0.67,
        },
    }
    immutable_hash = save_evidence(payload, args.out, args.db)
    print(json.dumps({"output": str(args.out), "status": payload["status"], "bet_eligible": bet_eligible, "hash": immutable_hash}, ensure_ascii=False))


if __name__ == "__main__":
    main()
