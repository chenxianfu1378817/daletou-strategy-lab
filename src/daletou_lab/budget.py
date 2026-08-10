from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .evidence import Evidence
from .models import ModelScores
from .optimizer import PortfolioPlan, build_plan, plan_structure_metrics
from .rules import LotteryRule


MODE_KEYS = {"单式": "Single", "复式": "Multiple", "混合": "Hybrid"}


@dataclass(frozen=True)
class CandidateComparison:
    mode: str
    plan: PortfolioPlan
    metrics: Mapping[str, Any]
    score: float
    meets_bet_standard: bool


@dataclass(frozen=True)
class BetDecision:
    decision: str
    bet_score: float
    suggested_amount: int
    reasons: tuple[str, ...]
    plan: PortfolioPlan
    selected_candidate: str | None
    comparisons: tuple[CandidateComparison, ...]


def _skip_plan(budget_limit: int) -> PortfolioPlan:
    return PortfolioPlan("不投注", (), (), 0, budget_limit)


def _historical_metrics(evidence: Evidence, budget_limit: int, mode_key: str) -> Mapping[str, Any]:
    budgets = evidence.payload.get("candidate_backtests", {})
    budget = budgets.get(str(budget_limit), {}) if isinstance(budgets, Mapping) else {}
    metrics = budget.get(mode_key, {}) if isinstance(budget, Mapping) else {}
    return metrics if isinstance(metrics, Mapping) else {}


def _candidate_score(metrics: Mapping[str, Any]) -> float:
    roi = float(metrics.get("historical_oos_roi", -1.0))
    excess = float(metrics.get("excess_roi_vs_random", -1.0))
    drawdown_ratio = float(metrics.get("maximum_drawdown_ratio", 1.0))
    monte_carlo = float(metrics.get("monte_carlo_profit_probability", 0.0))
    jackpot = float(metrics.get("jackpot_sensitivity", 1.0))
    overlap = float(metrics.get("combination_overlap", 1.0))
    coverage = float(metrics.get("coverage_score", 0.0))
    return (
        max(-1.0, min(1.0, roi)) * 0.22
        + max(-1.0, min(1.0, excess)) * 0.24
        + monte_carlo * 0.18
        + coverage * 0.14
        + (1.0 - min(1.0, drawdown_ratio)) * 0.10
        + (1.0 - min(1.0, jackpot)) * 0.07
        + (1.0 - min(1.0, overlap)) * 0.05
    )


def _meets_standard(evidence: Evidence, metrics: Mapping[str, Any]) -> bool:
    required = (
        "historical_oos_roi", "excess_roi_vs_random", "maximum_drawdown",
        "monte_carlo_profit_probability", "jackpot_sensitivity",
    )
    if not evidence.bet_eligible or any(not isinstance(metrics.get(key), (int, float)) for key in required):
        return False
    return (
        float(metrics["historical_oos_roi"]) > 0
        and float(metrics["excess_roi_vs_random"]) > 0
        and float(metrics.get("random_percentile", 0)) >= 0.95
        and float(metrics.get("roi_excluding_largest_win", -1)) > 0
        and float(metrics["monte_carlo_profit_probability"]) > 0.5
    )


def compare_candidates(
    scores: ModelScores,
    rule: LotteryRule,
    budget_limit: int,
    evidence: Evidence,
    seed: int,
) -> tuple[CandidateComparison, ...]:
    comparisons = []
    for chinese_mode, mode_key in MODE_KEYS.items():
        plan = build_plan(scores, rule, budget_limit, chinese_mode, seed)
        metrics = dict(plan_structure_metrics(plan))
        metrics.update(_historical_metrics(evidence, budget_limit, mode_key))
        metrics["coverage_score"] = min(
            1.0,
            (metrics["front_coverage"] / rule.front_pool) * 0.55
            + (metrics["back_coverage"] / rule.back_pool) * 0.30
            + (metrics["front_pair_coverage"] / 120) * 0.15,
        )
        comparisons.append(
            CandidateComparison(
                mode_key,
                plan,
                metrics,
                _candidate_score(metrics),
                _meets_standard(evidence, metrics),
            )
        )
    return tuple(comparisons)


def decide(
    scores: ModelScores,
    rule: LotteryRule,
    budget_limit: int,
    mode: str = "智能推荐",
    evidence: Evidence | None = None,
    seed: int = 0,
    precomputed_comparisons: tuple[CandidateComparison, ...] | None = None,
) -> BetDecision:
    if not 0 <= budget_limit <= 100:
        raise ValueError("预算必须在0到100元之间")
    if evidence is None:
        return BetDecision("SKIP", 0.0, 0, ("Evidence未提供，禁止用默认值代替",), _skip_plan(budget_limit), None, ())
    comparisons = precomputed_comparisons if precomputed_comparisons is not None else (
        compare_candidates(scores, rule, budget_limit, evidence, seed) if budget_limit >= rule.base_price else ()
    )
    if mode == "智能推荐":
        selected = max(comparisons, key=lambda item: item.score, default=None)
    else:
        wanted = MODE_KEYS.get(mode)
        if wanted is None:
            raise ValueError(f"未知推荐模式: {mode}")
        selected = next((item for item in comparisons if item.mode == wanted), None)
    reasons = list(evidence.problems)
    if not evidence.bet_eligible:
        reasons.insert(0, f"Evidence状态为{evidence.status}，不满足BET条件")
    if selected is None:
        reasons.append("预算为0或无可比较候选方案")
    elif not selected.meets_bet_standard:
        reasons.append(f"{selected.mode}候选的真实样本外指标未达BET阈值")
    if selected is None or not selected.meets_bet_standard:
        return BetDecision(
            "SKIP", selected.score if selected else 0.0, 0,
            tuple(dict.fromkeys(reasons or ["真实证据不足"])),
            _skip_plan(budget_limit), selected.mode if selected else None, comparisons,
        )
    return BetDecision(
        "BET", selected.score, selected.plan.cost,
        (f"{selected.mode}候选通过真实Evidence与统一Atomic Bet比较",),
        selected.plan, selected.mode, comparisons,
    )
