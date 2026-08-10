from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .atomic import AtomicBet, MultipleBet, portfolio_cost
from .models import ModelScores
from .rules import LotteryRule


def overlap(left: AtomicBet, right: AtomicBet) -> dict:
    front_common = len(set(left.front) & set(right.front))
    back_common = len(set(left.back) & set(right.back))
    front_union = len(set(left.front) | set(right.front))
    back_union = len(set(left.back) | set(right.back))
    return {
        "front_overlap": front_common,
        "back_overlap": back_common,
        "front_jaccard": front_common / front_union,
        "back_jaccard": back_common / back_union,
        "distance": 1 - ((front_common / front_union) * 0.7 + (back_common / back_union) * 0.3),
        "atomic_equal": left == right,
    }


def _candidate_pool(scores: ModelScores, rule: LotteryRule, seed: int, size: int = 240) -> List[AtomicBet]:
    generator = random.Random(seed)
    front_numbers = list(range(1, rule.front_pool + 1))
    back_numbers = list(range(1, rule.back_pool + 1))
    front_weights = [max(0.01, scores.front[n]) for n in front_numbers]
    back_weights = [max(0.01, scores.back[n]) for n in back_numbers]
    candidates = set()
    while len(candidates) < size:
        front = tuple(sorted(_weighted_sample_without_replacement(generator, front_numbers, front_weights, rule.front_pick)))
        back = tuple(sorted(_weighted_sample_without_replacement(generator, back_numbers, back_weights, rule.back_pick)))
        candidates.add(AtomicBet(front=front, back=back))
    return list(candidates)


def _weighted_sample_without_replacement(generator: random.Random, population: Sequence[int], weights: Sequence[float], count: int) -> List[int]:
    values, current_weights, result = list(population), list(weights), []
    for _ in range(count):
        choice = generator.choices(range(len(values)), weights=current_weights, k=1)[0]
        result.append(values.pop(choice))
        current_weights.pop(choice)
    return result


def greedy_coverage(scores: ModelScores, rule: LotteryRule, atomic_count: int, seed: int = 0) -> List[AtomicBet]:
    candidates = _candidate_pool(scores, rule, seed)
    selected: List[AtomicBet] = []
    covered_front: Set[Tuple[int, int]] = set()
    covered_back: Set[int] = set()
    for _ in range(max(0, atomic_count)):
        def utility(bet: AtomicBet) -> float:
            signal = sum(scores.front[n] for n in bet.front) + sum(scores.back[n] for n in bet.back)
            new_pairs = sum(1 for pair in combinations(bet.front, 2) if pair not in covered_front)
            new_back = sum(1 for n in bet.back if n not in covered_back)
            redundancy = sum(max(0.0, overlap(bet, chosen)["front_jaccard"] - 0.35) for chosen in selected)
            return signal + new_pairs * 0.18 + new_back * 0.45 - redundancy * 1.6

        choice = max(candidates, key=utility)
        selected.append(choice)
        candidates.remove(choice)
        covered_front.update(combinations(choice.front, 2))
        covered_back.update(choice.back)
    return selected


def signal_ranked(scores: ModelScores, rule: LotteryRule, atomic_count: int, seed: int = 0) -> List[AtomicBet]:
    """Model-only portfolio: rank unique candidates by score without a coverage reward."""
    candidates = _candidate_pool(scores, rule, seed)
    return sorted(
        candidates,
        key=lambda bet: sum(scores.front[n] for n in bet.front) + sum(scores.back[n] for n in bet.back),
        reverse=True,
    )[: max(0, atomic_count)]


@dataclass(frozen=True)
class PortfolioPlan:
    bet_type: str
    atomic_bets: Tuple[AtomicBet, ...]
    compounds: Tuple[MultipleBet, ...]
    cost: int
    unused_budget: int


def build_plan(
    scores: ModelScores,
    rule: LotteryRule,
    budget_limit: int,
    mode: str = "智能推荐",
    seed: int = 0,
    coverage_bets: Sequence[AtomicBet] | None = None,
) -> PortfolioPlan:
    if not 0 <= budget_limit <= 100:
        raise ValueError("预算必须在0到100元之间")
    if budget_limit < rule.base_price:
        return PortfolioPlan("不投注", (), (), 0, budget_limit)
    atomic_limit = budget_limit // rule.base_price
    if mode == "智能推荐":
        raise ValueError("智能推荐必须通过Single / Multiple / Hybrid真实指标比较，不得直接生成")
    if mode == "单式":
        bets = tuple((coverage_bets or greedy_coverage(scores, rule, atomic_limit, seed))[:atomic_limit])
        cost = portfolio_cost(bets, rule)
        return PortfolioPlan("单式", bets, (), cost, budget_limit - cost)
    ranked_front = tuple(sorted(scores.front, key=scores.front.get, reverse=True))
    ranked_back = tuple(sorted(scores.back, key=scores.back.get, reverse=True))
    candidates = []
    for front_count in range(6, 9):
        for back_count in range(2, 5):
            bet = MultipleBet(ranked_front[:front_count], ranked_back[:back_count])
            cost = bet.cost(rule)
            if cost <= budget_limit:
                candidates.append((cost, bet))
    if mode == "复式" and candidates:
        _, compound = max(candidates, key=lambda item: item[0])
        atoms = tuple(compound.expand(rule))
        cost = compound.cost(rule)
        return PortfolioPlan("复式", atoms, (compound,), cost, budget_limit - cost)
    if mode == "混合" and candidates:
        affordable = [item for item in candidates if item[0] <= budget_limit * 0.7]
        cost, compound = max(affordable or candidates, key=lambda item: item[0])
        remaining = (budget_limit - cost) // rule.base_price
        compound_atoms = tuple(compound.expand(rule))
        source = coverage_bets or greedy_coverage(scores, rule, remaining + len(compound_atoms), seed)
        extras = [bet for bet in source[: remaining + len(compound_atoms)] if bet not in compound_atoms][:remaining]
        atoms = compound_atoms + tuple(extras)
        total_cost = cost + portfolio_cost(extras, rule)
        return PortfolioPlan("混合", atoms, (compound,), total_cost, budget_limit - total_cost)
    return build_plan(scores, rule, budget_limit, "单式", seed, coverage_bets)


def plan_structure_metrics(plan: PortfolioPlan) -> Dict[str, float]:
    atoms = tuple(plan.atomic_bets)
    front_numbers = {number for bet in atoms for number in bet.front}
    back_numbers = {number for bet in atoms for number in bet.back}
    front_pairs = {pair for bet in atoms for pair in combinations(bet.front, 2)}
    pair_overlaps = []
    for index, left in enumerate(atoms):
        for right in atoms[index + 1 :]:
            detail = overlap(left, right)
            pair_overlaps.append(detail["front_jaccard"] * 0.7 + detail["back_jaccard"] * 0.3)
    return {
        "actual_cost": plan.cost,
        "atomic_bets": len(atoms),
        "front_coverage": len(front_numbers),
        "back_coverage": len(back_numbers),
        "front_pair_coverage": len(front_pairs),
        "combination_overlap": sum(pair_overlaps) / len(pair_overlaps) if pair_overlaps else 0.0,
    }
