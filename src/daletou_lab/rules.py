from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULE_DIR = PROJECT_ROOT / "config" / "lottery_rules"


@dataclass(frozen=True)
class PrizeLevel:
    level: int
    matches: Tuple[Tuple[int, int], ...]
    kind: str
    amount: Optional[int] = None
    high_pool_amount: Optional[int] = None


@dataclass(frozen=True)
class LotteryRule:
    rule_version: str
    effective_from_issue: int
    effective_to_issue: Optional[int]
    front_pool: int
    front_pick: int
    back_pool: int
    back_pick: int
    base_price: int
    additional_price: int
    additional_ratio: float
    additional_levels: Tuple[int, ...]
    prize_levels: Tuple[PrizeLevel, ...]
    high_pool_threshold: Optional[int]
    source: str

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "LotteryRule":
        levels = tuple(
            PrizeLevel(
                level=int(item["level"]),
                matches=tuple(tuple(pair) for pair in item["matches"]),
                kind=item["type"],
                amount=item.get("amount"),
                high_pool_amount=item.get("high_pool_amount"),
            )
            for item in raw["prize_levels"]
        )
        return cls(
            rule_version=raw["rule_version"],
            effective_from_issue=int(raw["effective_from_issue"]),
            effective_to_issue=(int(raw["effective_to_issue"]) if raw.get("effective_to_issue") else None),
            front_pool=int(raw["front_pool"]),
            front_pick=int(raw["front_pick"]),
            back_pool=int(raw["back_pool"]),
            back_pick=int(raw["back_pick"]),
            base_price=int(raw["base_price"]),
            additional_price=int(raw["additional_price"]),
            additional_ratio=float(raw["additional_ratio"]),
            additional_levels=tuple(int(v) for v in raw["additional_levels"]),
            prize_levels=levels,
            high_pool_threshold=raw.get("high_pool_threshold"),
            source=raw["source"],
        )

    def prize_level_for(self, front_matches: int, back_matches: int) -> Optional[PrizeLevel]:
        pair = (front_matches, back_matches)
        return next((level for level in self.prize_levels if pair in level.matches), None)


class RuleRegistry:
    def __init__(self, rule_dir: Path = RULE_DIR):
        self.rule_dir = rule_dir
        self._rules = self._load()

    def _load(self) -> Tuple[LotteryRule, ...]:
        rules: List[LotteryRule] = []
        for path in sorted(self.rule_dir.glob("rule_*.json")):
            with path.open("r", encoding="utf-8") as handle:
                rules.append(LotteryRule.from_dict(json.load(handle)))
        if not rules:
            raise RuntimeError(f"No rule configuration found in {self.rule_dir}")
        return tuple(sorted(rules, key=lambda rule: rule.effective_from_issue))

    @property
    def rules(self) -> Tuple[LotteryRule, ...]:
        return self._rules

    def for_issue(self, issue: str | int) -> LotteryRule:
        issue_num = int(issue)
        matches = [
            rule
            for rule in self._rules
            if issue_num >= rule.effective_from_issue
            and (rule.effective_to_issue is None or issue_num <= rule.effective_to_issue)
        ]
        if not matches:
            raise LookupError(f"No audited rule version for issue {issue_num}")
        return matches[-1]

    def current(self) -> LotteryRule:
        return self._rules[-1]


def validate_numbers(front: Iterable[int], back: Iterable[int], rule: LotteryRule) -> None:
    front_tuple, back_tuple = tuple(front), tuple(back)
    if len(front_tuple) != rule.front_pick or len(back_tuple) != rule.back_pick:
        raise ValueError("单式必须为前区5个、后区2个号码")
    if len(set(front_tuple)) != len(front_tuple) or len(set(back_tuple)) != len(back_tuple):
        raise ValueError("同一区号码不得重复")
    if any(number < 1 or number > rule.front_pool for number in front_tuple):
        raise ValueError("前区号码超出范围")
    if any(number < 1 or number > rule.back_pool for number in back_tuple):
        raise ValueError("后区号码超出范围")

