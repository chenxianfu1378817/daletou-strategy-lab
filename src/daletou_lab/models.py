from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from .atomic import AtomicBet
from .database import Draw
from .rules import LotteryRule


ScoreMap = Dict[int, float]


@dataclass(frozen=True)
class ModelScores:
    front: ScoreMap
    back: ScoreMap
    uncertainty: float
    diagnostics: Mapping[str, float]


class NumberModel(ABC):
    name = "base"

    @abstractmethod
    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        raise NotImplementedError

    def pick(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> AtomicBet:
        scores = self.score(history, rule, seed)
        front = tuple(sorted(sorted(scores.front, key=scores.front.get, reverse=True)[: rule.front_pick]))
        back = tuple(sorted(sorted(scores.back, key=scores.back.get, reverse=True)[: rule.back_pick]))
        return AtomicBet(front=front, back=back)


def _normalize(values: Mapping[int, float]) -> ScoreMap:
    if not values:
        return {}
    minimum, maximum = min(values.values()), max(values.values())
    if math.isclose(minimum, maximum):
        return {key: 0.5 for key in values}
    return {key: (value - minimum) / (maximum - minimum) for key, value in values.items()}


class RandomModel(NumberModel):
    name = "Random"

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        generator = random.Random(seed)
        return ModelScores(
            front={n: generator.random() for n in range(1, rule.front_pool + 1)},
            back={n: generator.random() for n in range(1, rule.back_pool + 1)},
            uncertainty=1.0,
            diagnostics={"history_size": float(len(history))},
        )


class FrequencyModel(NumberModel):
    name = "Frequency"

    def __init__(self, window: int = 120):
        self.window = window

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        sample = history[-self.window :]
        front_counts = Counter(n for draw in sample for n in draw.front)
        back_counts = Counter(n for draw in sample for n in draw.back)
        return ModelScores(
            front=_normalize({n: front_counts[n] for n in range(1, rule.front_pool + 1)}),
            back=_normalize({n: back_counts[n] for n in range(1, rule.back_pool + 1)}),
            uncertainty=min(1.0, 80 / max(1, len(sample))),
            diagnostics={"window": float(len(sample))},
        )


class HotColdModel(NumberModel):
    name = "HotCold"

    def __init__(self, short_window: int = 30, long_window: int = 180):
        self.short_window = short_window
        self.long_window = long_window

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        short, long = history[-self.short_window :], history[-self.long_window :]
        short_front = Counter(n for draw in short for n in draw.front)
        long_front = Counter(n for draw in long for n in draw.front)
        short_back = Counter(n for draw in short for n in draw.back)
        long_back = Counter(n for draw in long for n in draw.back)
        front = {
            n: short_front[n] / max(1, len(short)) - long_front[n] / max(1, len(long))
            for n in range(1, rule.front_pool + 1)
        }
        back = {
            n: short_back[n] / max(1, len(short)) - long_back[n] / max(1, len(long))
            for n in range(1, rule.back_pool + 1)
        }
        return ModelScores(_normalize(front), _normalize(back), 0.9, {"short_window": len(short), "long_window": len(long)})


class BayesianModel(NumberModel):
    name = "Bayesian"

    def __init__(self, window: int = 180, prior_strength: float = 20.0):
        self.window, self.prior_strength = window, prior_strength

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        sample = history[-self.window :]
        front_counts = Counter(n for draw in sample for n in draw.front)
        back_counts = Counter(n for draw in sample for n in draw.back)
        expected_front = rule.front_pick / rule.front_pool
        expected_back = rule.back_pick / rule.back_pool
        denominator = len(sample) + self.prior_strength
        front = {n: (front_counts[n] + self.prior_strength * expected_front) / max(1, denominator) for n in range(1, rule.front_pool + 1)}
        back = {n: (back_counts[n] + self.prior_strength * expected_back) / max(1, denominator) for n in range(1, rule.back_pool + 1)}
        return ModelScores(_normalize(front), _normalize(back), min(1.0, 60 / max(1, len(sample))), {"prior_strength": self.prior_strength})


class EntropyModel(NumberModel):
    name = "Entropy"

    def __init__(self, window: int = 120):
        self.window = window

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        frequency = FrequencyModel(self.window).score(history, rule, seed)
        front = {n: 1.0 - abs(value - 0.5) * 2 for n, value in frequency.front.items()}
        back = {n: 1.0 - abs(value - 0.5) * 2 for n, value in frequency.back.items()}
        return ModelScores(_normalize(front), _normalize(back), 0.85, {"window": min(self.window, len(history))})


class CoOccurrenceModel(NumberModel):
    name = "CoOccurrence"

    def __init__(self, window: int = 180):
        self.window = window

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        sample = history[-self.window :]
        front_pair = Counter()
        back_pair = Counter()
        for draw in sample:
            for left in draw.front:
                for right in draw.front:
                    if left < right:
                        front_pair[(left, right)] += 1
            back_pair[tuple(draw.back)] += 1
        front = {n: sum(count for pair, count in front_pair.items() if n in pair) for n in range(1, rule.front_pool + 1)}
        back = {n: sum(count for pair, count in back_pair.items() if n in pair) for n in range(1, rule.back_pool + 1)}
        return ModelScores(_normalize(front), _normalize(back), 0.9, {"pair_count": len(front_pair) + len(back_pair)})


class EnsembleModel(NumberModel):
    name = "Ensemble"

    def __init__(self):
        self.members = (FrequencyModel(), BayesianModel(), EntropyModel(), CoOccurrenceModel())

    def score(self, history: Sequence[Draw], rule: LotteryRule, seed: int = 0) -> ModelScores:
        member_scores = [member.score(history, rule, seed + index) for index, member in enumerate(self.members)]
        front = {n: sum(scores.front[n] for scores in member_scores) / len(member_scores) for n in range(1, rule.front_pool + 1)}
        back = {n: sum(scores.back[n] for scores in member_scores) / len(member_scores) for n in range(1, rule.back_pool + 1)}
        disagreement = sum(
            max(scores.front[n] for scores in member_scores) - min(scores.front[n] for scores in member_scores)
            for n in range(1, rule.front_pool + 1)
        ) / rule.front_pool
        return ModelScores(front, back, min(1.0, 0.55 + disagreement), {"model_disagreement": disagreement})


MODEL_REGISTRY = {
    model.name: model
    for model in (RandomModel(), FrequencyModel(), HotColdModel(), BayesianModel(), EntropyModel(), CoOccurrenceModel(), EnsembleModel())
}

