#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from daletou_lab.database import DEFAULT_DB, load_draws


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data" / "app-data.json"
RECOMMENDATION = ROOT / "data" / "exports" / "recommendation.json"
ABLATION = ROOT / "data" / "exports" / "ablation-v1.1.0.json"


def main() -> None:
    draws = load_draws(DEFAULT_DB)
    if not draws:
        raise SystemExit("No verified draws")
    if not RECOMMENDATION.exists():
        raise SystemExit("recommendation.json is required; web builder never generates official numbers")
    recommendation = json.loads(RECOMMENDATION.read_text(encoding="utf-8"))
    latest = draws[-1]
    recommendation_source_issue = str(int(recommendation["issue"]) - 1)
    if recommendation_source_issue != latest.issue:
        recommendation = dict(recommendation)
        recommendation["decision"] = "SKIP"
        recommendation["recommended_budget"] = 0
        recommendation["bet_type"] = "不投注"
        recommendation["numbers"] = []
        recommendation["evidence"] = dict(recommendation.get("evidence", {}))
        recommendation["evidence"]["status"] = "STALE"
        recommendation["evidence"]["bet_eligible"] = False
        recommendation["evidence"].setdefault("problems", []).append("正式推荐与最新已验证开奖期不匹配")
        for modes in recommendation.get("plans", {}).values():
            for plan in modes.values():
                plan.update({"decision": "SKIP", "recommended_budget": 0, "actual_cost": 0, "numbers": [], "atomic_bets": [], "atomic_bet_count": 0})
                plan.setdefault("reasons", []).insert(0, "Evidence或正式推荐已过期")
    ablation = json.loads(ABLATION.read_text(encoding="utf-8")) if ABLATION.exists() else {"ablation": {}}
    backtests = [row for window in ("100", "300", "500") for row in ablation.get("ablation", {}).get(window, [])]
    payload = {
        "version": "1.1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "China Sports Lottery official gateway",
        "latest": {
            "issue": latest.issue, "drawDate": latest.draw_date, "front": latest.front, "back": latest.back,
            "jackpotAfter": latest.jackpot_after, "ruleVersion": latest.rule_version, "verified": latest.verified,
        },
        "history": {"count": len(draws), "firstIssue": draws[0].issue, "lastIssue": latest.issue},
        "recommendation": {
            "issue": recommendation["issue"], "generatedAt": recommendation["generated_at"],
            "decision": recommendation["decision"], "suggestedAmount": recommendation["recommended_budget"],
            "budgetLimit": recommendation["budget_limit"], "mode": "Smart", "betType": recommendation["bet_type"],
            "reasons": recommendation["evidence"].get("problems", []),
            "uncertainty": 1.0 - float(recommendation["evidence"].get("model_stability") or 0),
            "numbers": recommendation["numbers"], "evidence": recommendation["evidence"],
            "plans": recommendation["plans"], "modelVersion": recommendation["model_version"],
            "strategyVersion": recommendation["strategy_version"], "randomSeed": recommendation["random_seed"],
            "gitCommitHash": recommendation["git_commit_hash"], "immutableHash": recommendation["immutable_hash"],
            "officialNumbersSource": recommendation["official_numbers_source"],
        },
        "backtests": backtests,
        "validation": {
            "training": "complete", "validation": recommendation["evidence"].get("validation_status", "unknown"),
            "holdout": recommendation["evidence"].get("holdout_status", "unknown"),
            "forward": f"{recommendation['evidence'].get('forward_periods', 0)} settled periods",
            "evidence": recommendation["evidence"].get("status", "INVALID"),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(OUT.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(OUT)
    print(json.dumps({"output": str(OUT), "draws": len(draws), "decision": recommendation["decision"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
