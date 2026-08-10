#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from daletou_lab.budget import compare_candidates, decide
from daletou_lab.database import connect, initialize, load_draws
from daletou_lab.evidence import load_evidence
from daletou_lab.models import EnsembleModel
from daletou_lab.rules import RuleRegistry


BUDGETS = (0, 20, 30, 40, 50, 60, 70, 80, 90, 100)
MODES = (("智能推荐", "Smart"), ("单式", "Single"), ("复式", "Multiple"), ("混合", "Hybrid"))
STRATEGY_VERSION = "V1.1.0"
MODEL_VERSION = "Ensemble_v1"


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def comparison_payload(comparison) -> dict:
    return {
        "mode": comparison.mode,
        "score": comparison.score,
        "meets_bet_standard": comparison.meets_bet_standard,
        "metrics": dict(comparison.metrics),
        "candidate_cost": comparison.plan.cost,
        "candidate_atomic_bets": [bet.text() for bet in comparison.plan.atomic_bets],
        "official": False,
    }


def decision_payload(decision, budget: int, mode_key: str) -> dict:
    official_numbers = [bet.text() for bet in decision.plan.atomic_bets] if decision.decision == "BET" else []
    return {
        "decision": decision.decision,
        "budget_limit": budget,
        "recommended_budget": decision.suggested_amount,
        "mode": mode_key,
        "bet_type": decision.plan.bet_type,
        "numbers": official_numbers,
        "atomic_bets": official_numbers,
        "atomic_bet_count": len(official_numbers),
        "actual_cost": decision.plan.cost if decision.decision == "BET" else 0,
        "unused_budget": budget - decision.suggested_amount,
        "reasons": list(decision.reasons),
        "bet_score": decision.bet_score,
        "selected_candidate": decision.selected_candidate,
        "comparisons": [comparison_payload(item) for item in decision.comparisons],
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(path)


def ensure_paper_bet(connection, prediction_id: int, payload: dict) -> None:
    paper_payload = {
        "issue": payload["issue"], "decision": payload["decision"],
        "cost": payload["recommended_budget"], "bet_type": payload["bet_type"],
        "numbers": payload["numbers"], "strategy_version": payload["strategy_version"],
        "immutable_hash": payload["immutable_hash"],
    }
    connection.execute(
        "INSERT OR IGNORE INTO paper_bets(prediction_id,strategy_id,payload_json) VALUES(?,?,?)",
        (prediction_id, STRATEGY_VERSION, json.dumps(paper_payload, ensure_ascii=False)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the immutable V1.1.0 recommendation matrix")
    parser.add_argument("--db", type=Path, default=Path("data/daletou.db"))
    parser.add_argument("--evidence", type=Path, default=Path("data/exports/evidence.json"))
    parser.add_argument("--out", type=Path, default=Path("data/exports/recommendation.json"))
    args = parser.parse_args()
    initialize(args.db)
    draws = load_draws(args.db)
    if not draws:
        raise SystemExit("No verified history in database")
    latest = draws[-1]
    issue = str(int(latest.issue) + 1)
    evidence = load_evidence(args.evidence, latest.issue)
    seed = int(hashlib.sha256(f"{issue}:{STRATEGY_VERSION}".encode()).hexdigest()[:12], 16)
    with connect(args.db) as connection:
        existing = connection.execute(
            "SELECT prediction_id,explanation_json FROM predictions WHERE issue=? AND strategy_version=? LIMIT 1",
            (issue, STRATEGY_VERSION),
        ).fetchone()
    if existing is not None:
        stored = json.loads(existing["explanation_json"])
        payload = stored["snapshot"]
        with connect(args.db) as connection:
            ensure_paper_bet(connection, int(existing["prediction_id"]), payload)
        write_json(args.out, payload)
        print(json.dumps({"output": str(args.out), "issue": issue, "reused_immutable": True, "decision": payload["decision"]}, ensure_ascii=False))
        return

    rule = RuleRegistry().current()
    scores = EnsembleModel().score(draws, rule, seed=seed)
    plans = {}
    for budget in BUDGETS:
        plans[str(budget)] = {}
        comparisons = compare_candidates(scores, rule, budget, evidence, seed) if budget >= rule.base_price else ()
        for chinese_mode, mode_key in MODES:
            result = decide(scores, rule, budget, chinese_mode, evidence, seed, comparisons)
            plans[str(budget)][mode_key] = decision_payload(result, budget, mode_key)
    canonical = plans["100"]["Smart"]
    generated_at = datetime.now(timezone.utc).isoformat()
    commit = git_commit()
    payload = {
        "schema_version": "recommendation-v1.1",
        "issue": issue,
        "generated_at": generated_at,
        "decision": canonical["decision"],
        "budget_limit": 100,
        "recommended_budget": canonical["recommended_budget"],
        "bet_type": canonical["bet_type"],
        "numbers": canonical["numbers"],
        "model_version": MODEL_VERSION,
        "strategy_version": STRATEGY_VERSION,
        "evidence": evidence.summary(),
        "random_seed": seed,
        "git_commit_hash": commit,
        "plans": plans,
        "official_numbers_source": "Python backend only",
        "immutable": True,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    immutable_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    payload["immutable_hash"] = immutable_hash
    with connect(args.db) as connection:
        cursor = connection.execute(
            """INSERT INTO predictions(issue,created_at,decision,budget_limit,recommended_amount,
            bet_type,numbers_json,explanation_json,model_version,feature_version,optimizer_version,
            budget_version,rule_version,code_commit_hash,strategy_version,evidence_status,evidence_json,
            random_seed,immutable_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                issue, generated_at, canonical["decision"], 100, canonical["recommended_budget"],
                canonical["bet_type"], json.dumps(canonical["numbers"], ensure_ascii=False),
                json.dumps({"snapshot": payload}, ensure_ascii=False), MODEL_VERSION, "features_v1",
                "atomic_compare_v1.1", "budget_smart_v1.1", rule.rule_version, commit, STRATEGY_VERSION,
                evidence.status, json.dumps(evidence.summary(), ensure_ascii=False), seed, immutable_hash,
            ),
        )
        ensure_paper_bet(connection, int(cursor.lastrowid), payload)
    write_json(args.out, payload)
    print(json.dumps({"output": str(args.out), "issue": issue, "decision": payload["decision"], "evidence_status": evidence.status}, ensure_ascii=False))


if __name__ == "__main__":
    main()
