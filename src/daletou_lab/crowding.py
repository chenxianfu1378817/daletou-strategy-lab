from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .atomic import AtomicBet


@dataclass(frozen=True)
class CrowdingProxy:
    score: float
    birthday_share: float
    arithmetic_sequence: bool
    symmetric_pattern: bool
    repeated_endings: int
    note: str = "Popularity Proxy；不代表真实投注人数，也不改变开奖概率。"


def score_crowding(bet: AtomicBet) -> CrowdingProxy:
    all_numbers = tuple(bet.front) + tuple(bet.back)
    birthday_share = sum(number <= 31 for number in bet.front) / len(bet.front)
    front_gaps = [right - left for left, right in zip(bet.front, bet.front[1:])]
    arithmetic = bool(front_gaps and len(set(front_gaps)) == 1)
    symmetric = bet.front[0] + bet.front[-1] == bet.front[1] + bet.front[-2]
    endings = len(all_numbers) - len({number % 10 for number in all_numbers})
    score = min(1.0, birthday_share * 0.35 + arithmetic * 0.3 + symmetric * 0.2 + endings * 0.08)
    return CrowdingProxy(score, birthday_share, arithmetic, symmetric, endings)

