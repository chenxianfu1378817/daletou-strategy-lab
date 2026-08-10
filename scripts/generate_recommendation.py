#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from daletou_lab.budget import decide
from daletou_lab.database import connect, load_draws
from daletou_lab.models import EnsembleModel
from daletou_lab.rules import RuleRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and append an immutable next-issue recommendation")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument("--mode", choices=["智能推荐", "单式", "复式", "混合"], default="智能推荐")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    draws = load_draws(args.db)
    if not draws:
        raise SystemExit("No verified history in database")
    evidence = json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else {}
    current = draws[-1]
    rule = RuleRegistry().current()
    scores = EnsembleModel().score(draws, rule, seed=int(current.issue))
    decision = decide(scores, rule, args.budget, args.mode, evidence, seed=int(current.issue))
    issue = str(int(current.issue) + 1)
    numbers = [bet.text() for bet in decision.plan.atomic_bets]
    payload = {
        "issue": issue,
        "decision": decision.decision,
        "budget_limit": args.budget,
        "recommended_amount": decision.suggested_amount,
        "bet_type": decision.plan.bet_type,
        "numbers": numbers,
        "reasons": decision.reasons,
        "bet_score": decision.bet_score,
    }
    immutable_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "uncommitted"
    with connect(args.db) as connection:
        connection.execute(
            """INSERT OR IGNORE INTO predictions(issue,created_at,decision,budget_limit,recommended_amount,
            bet_type,numbers_json,explanation_json,model_version,feature_version,optimizer_version,
            budget_version,rule_version,code_commit_hash,immutable_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                issue,
                datetime.now(timezone.utc).isoformat(),
                decision.decision,
                args.budget,
                decision.suggested_amount,
                decision.plan.bet_type,
                json.dumps(numbers, ensure_ascii=False),
                json.dumps({"reasons": decision.reasons, "bet_score": decision.bet_score}, ensure_ascii=False),
                "Ensemble_v1",
                "features_v1",
                "coverage_v1",
                "budget_v1",
                rule.rule_version,
                commit,
                immutable_hash,
            ),
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

