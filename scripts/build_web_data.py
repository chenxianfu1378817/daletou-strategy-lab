#!/usr/bin/env python3
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from daletou_lab.database import DEFAULT_DB, connect, load_draws
from daletou_lab.models import EnsembleModel
from daletou_lab.budget import decide
from daletou_lab.rules import RuleRegistry


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draws = load_draws(DEFAULT_DB)
    if not draws:
        raise SystemExit("No verified draws")
    latest = draws[-1]
    registry = RuleRegistry()
    rule = registry.current()
    scores = EnsembleModel().score(draws, rule, seed=int(latest.issue))
    decision = decide(scores, rule, 100, "智能推荐", {}, seed=int(latest.issue))
    backtest_path = ROOT / "data" / "exports" / "backtest.json"
    backtests = json.loads(backtest_path.read_text(encoding="utf-8")) if backtest_path.exists() else []
    payload = {
        "version": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "China Sports Lottery official gateway",
        "latest": {
            "issue": latest.issue,
            "drawDate": latest.draw_date,
            "front": latest.front,
            "back": latest.back,
            "jackpotAfter": latest.jackpot_after,
            "ruleVersion": latest.rule_version,
            "verified": latest.verified,
        },
        "history": {"count": len(draws), "firstIssue": draws[0].issue, "lastIssue": latest.issue},
        "recommendation": {
            "issue": str(int(latest.issue) + 1),
            "decision": decision.decision,
            "suggestedAmount": decision.suggested_amount,
            "budgetLimit": 100,
            "mode": "智能推荐",
            "betType": decision.plan.bet_type,
            "reasons": decision.reasons,
            "uncertainty": scores.uncertainty,
            "researchNumbers": [bet.text() for bet in decision.plan.atomic_bets[:5]],
        },
        "backtests": backtests,
        "validation": {"training": "complete", "validation": "complete", "holdout": "locked", "forward": "collecting"},
    }
    temporary = OUT / "app-data.json.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(OUT / "app-data.json")
    print(json.dumps({"output": str(OUT / "app-data.json"), "draws": len(draws)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

