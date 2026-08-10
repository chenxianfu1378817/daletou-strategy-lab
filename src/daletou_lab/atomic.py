from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Iterable, Iterator, Tuple

from .rules import LotteryRule, validate_numbers


@dataclass(frozen=True, order=True)
class AtomicBet:
    front: Tuple[int, int, int, int, int]
    back: Tuple[int, int]
    additional: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "front", tuple(sorted(self.front)))
        object.__setattr__(self, "back", tuple(sorted(self.back)))

    def validate(self, rule: LotteryRule) -> None:
        validate_numbers(self.front, self.back, rule)

    def cost(self, rule: LotteryRule) -> int:
        return rule.base_price + (rule.additional_price if self.additional else 0)

    def text(self) -> str:
        return " ".join(f"{n:02d}" for n in self.front) + " + " + " ".join(f"{n:02d}" for n in self.back)


@dataclass(frozen=True)
class MultipleBet:
    front: Tuple[int, ...]
    back: Tuple[int, ...]
    additional: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "front", tuple(sorted(set(self.front))))
        object.__setattr__(self, "back", tuple(sorted(set(self.back))))

    def validate(self, rule: LotteryRule) -> None:
        if len(self.front) < rule.front_pick or len(self.back) < rule.back_pick:
            raise ValueError("复式号码数量不足")
        if any(n < 1 or n > rule.front_pool for n in self.front):
            raise ValueError("前区号码超出范围")
        if any(n < 1 or n > rule.back_pool for n in self.back):
            raise ValueError("后区号码超出范围")

    def atomic_count(self, rule: LotteryRule) -> int:
        return comb(len(self.front), rule.front_pick) * comb(len(self.back), rule.back_pick)

    def cost(self, rule: LotteryRule) -> int:
        unit = rule.base_price + (rule.additional_price if self.additional else 0)
        return self.atomic_count(rule) * unit

    def expand(self, rule: LotteryRule) -> Iterator[AtomicBet]:
        self.validate(rule)
        for front in combinations(self.front, rule.front_pick):
            for back in combinations(self.back, rule.back_pick):
                yield AtomicBet(front=front, back=back, additional=self.additional)


def portfolio_cost(bets: Iterable[AtomicBet], rule: LotteryRule) -> int:
    return sum(bet.cost(rule) for bet in bets)

