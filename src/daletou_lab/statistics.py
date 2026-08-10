from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean, median
from typing import Callable, Iterable, List, Sequence


@dataclass(frozen=True)
class StatisticalResult:
    observed: float
    p_value: float
    bootstrap_ci: tuple
    effect_size: float
    hypotheses_tested: int
    adjusted_p_value: float
    significant_after_fdr: bool


def bootstrap_ci(values: Sequence[float], iterations: int = 1000, confidence: float = 0.95, seed: int = 0) -> tuple:
    if not values:
        return (0.0, 0.0)
    generator = random.Random(seed)
    estimates = sorted(mean(generator.choice(values) for _ in values) for _ in range(iterations))
    alpha = (1 - confidence) / 2
    low = estimates[int(alpha * (len(estimates) - 1))]
    high = estimates[int((1 - alpha) * (len(estimates) - 1))]
    return low, high


def permutation_test(actual: Sequence[float], baseline: Sequence[float], iterations: int = 1000, seed: int = 0, hypotheses_tested: int = 1) -> StatisticalResult:
    if not actual or not baseline:
        raise ValueError("Permutation test requires two non-empty samples")
    generator = random.Random(seed)
    observed = mean(actual) - mean(baseline)
    combined = list(actual) + list(baseline)
    count = 0
    for _ in range(iterations):
        generator.shuffle(combined)
        difference = mean(combined[: len(actual)]) - mean(combined[len(actual) :])
        if abs(difference) >= abs(observed):
            count += 1
    p_value = (count + 1) / (iterations + 1)
    adjusted = min(1.0, p_value * max(1, hypotheses_tested))
    pooled = ((sum((x - mean(actual)) ** 2 for x in actual) + sum((x - mean(baseline)) ** 2 for x in baseline)) / max(1, len(combined) - 2)) ** 0.5
    effect = observed / pooled if pooled else 0.0
    differences = [a - b for a, b in zip(actual, baseline)]
    return StatisticalResult(observed, p_value, bootstrap_ci(differences or [observed], seed=seed), effect, hypotheses_tested, adjusted, adjusted < 0.05)


def benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> List[bool]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    rejected = [False] * len(p_values)
    largest_rank = 0
    for rank, (_, value) in enumerate(indexed, start=1):
        if value <= alpha * rank / max(1, len(indexed)):
            largest_rank = rank
    for rank, (index, _) in enumerate(indexed, start=1):
        rejected[index] = rank <= largest_rank
    return rejected

