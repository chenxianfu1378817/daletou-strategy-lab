from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .models import ModelScores
from .optimizer import PortfolioPlan, build_plan
from .rules import LotteryRule


@dataclass(frozen=True)
class BetDecision:
    decision: str
    bet_score: float
    suggested_amount: int
    reasons: tuple
    plan: PortfolioPlan


def decide(
    scores: ModelScores,
    rule: LotteryRule,
    budget_limit: int,
    mode: str = "智能推荐",
    evidence: Mapping[str, float] | None = None,
    seed: int = 0,
) -> BetDecision:
    if not 0 <= budget_limit <= 100:
        raise ValueError("预算必须在0到100元之间")
    evidence = evidence or {}
    excess_roi = float(evidence.get("excess_roi", 0.0))
    random_percentile = float(evidence.get("random_percentile", 0.5))
    stability = float(evidence.get("stability", 0.0))
    forward_roi = float(evidence.get("forward_roi", -1.0))
    score = (
        max(0.0, min(1.0, 0.5 + excess_roi)) * 0.3
        + random_percentile * 0.25
        + stability * 0.2
        + max(0.0, min(1.0, 0.5 + forward_roi)) * 0.15
        + (1.0 - scores.uncertainty) * 0.1
    )
    reasons = []
    if excess_roi <= 0:
        reasons.append("样本外尚未形成正超额收益")
    if random_percentile < 0.95:
        reasons.append("尚未超过随机策略高分位")
    if scores.uncertainty > 0.5:
        reasons.append("模型不确定性较高")
    if stability < 0.6:
        reasons.append("跨窗口稳定性不足")
    should_bet = score >= 0.72 and budget_limit >= rule.base_price
    if not should_bet:
        plan = PortfolioPlan("不投注", (), (), 0, budget_limit)
        return BetDecision("SKIP", score, 0, tuple(reasons or ["当前风险收益比不理想"]), plan)
    fraction = 0.4 if score < 0.82 else 0.7
    suggested = min(budget_limit, int((budget_limit * fraction) // rule.base_price * rule.base_price))
    plan = build_plan(scores, rule, suggested, mode, seed)
    return BetDecision("BET", score, plan.cost, tuple(reasons or ["主要样本外证据满足预设阈值"]), plan)

