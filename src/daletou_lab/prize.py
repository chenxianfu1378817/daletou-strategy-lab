from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, Mapping, Optional, Tuple

from .atomic import AtomicBet
from .rules import LotteryRule


@dataclass(frozen=True)
class PrizeResult:
    level: Optional[int]
    front_matches: int
    back_matches: int
    base_prize: int
    additional_prize: int

    @property
    def gross_prize(self) -> int:
        return self.base_prize + self.additional_prize


def settle_atomic(
    bet: AtomicBet,
    winning_front: Iterable[int],
    winning_back: Iterable[int],
    rule: LotteryRule,
    realized_prizes: Optional[Mapping[int, int]] = None,
    pool_before: Optional[float] = None,
) -> PrizeResult:
    bet.validate(rule)
    front_matches = len(set(bet.front) & set(winning_front))
    back_matches = len(set(bet.back) & set(winning_back))
    level = rule.prize_level_for(front_matches, back_matches)
    if level is None:
        return PrizeResult(None, front_matches, back_matches, 0, 0)
    if realized_prizes and level.level in realized_prizes:
        base = int(realized_prizes[level.level])
    elif level.kind == "fixed" and level.amount is not None:
        high_pool = bool(
            rule.high_pool_threshold is not None
            and pool_before is not None
            and pool_before >= rule.high_pool_threshold
        )
        base = int(level.high_pool_amount if high_pool and level.high_pool_amount is not None else level.amount)
    else:
        raise ValueError("浮动奖历史结算必须提供当期官方实际单注奖金")
    additional = 0
    if bet.additional and level.level in rule.additional_levels:
        additional = int(round(base * rule.additional_ratio))
    return PrizeResult(level.level, front_matches, back_matches, base, additional)


def tax_for_issue(gross_prize: int, draw_date: date, threshold: int = 10000, rate: float = 0.2) -> int:
    if gross_prize <= threshold:
        return 0
    return int(round(gross_prize * rate))


def settle_portfolio(
    bets: Iterable[AtomicBet],
    winning_front: Iterable[int],
    winning_back: Iterable[int],
    rule: LotteryRule,
    draw_date: date,
    realized_prizes: Optional[Mapping[int, int]] = None,
    pool_before: Optional[float] = None,
) -> Dict[str, object]:
    results = [
        settle_atomic(bet, winning_front, winning_back, rule, realized_prizes, pool_before)
        for bet in bets
    ]
    gross = sum(item.gross_prize for item in results)
    tax = tax_for_issue(gross, draw_date)
    return {"results": results, "gross_prize": gross, "tax": tax, "net_prize": gross - tax}

