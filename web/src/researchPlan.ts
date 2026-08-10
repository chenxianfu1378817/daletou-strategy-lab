import type { OfficialPlan, RecommendationPlans } from './types'

export const modeKeys = {
  '智能推荐': 'Smart',
  '单式': 'Single',
  '复式': 'Multiple',
  '混合': 'Hybrid',
} as const

export type ModeLabel = keyof typeof modeKeys

export function emptyOfficialPlan(budget: number, mode: string, reason = '后台未提供对应正式方案'): OfficialPlan {
  return {
    decision: 'SKIP', budget_limit: budget, recommended_budget: 0, mode, bet_type: '不投注',
    numbers: [], atomic_bets: [], atomic_bet_count: 0, actual_cost: 0, unused_budget: budget,
    reasons: [reason], bet_score: 0, selected_candidate: null, comparisons: [],
  }
}

export function selectOfficialPlan(plans: RecommendationPlans, budget: number, mode: ModeLabel): OfficialPlan {
  const selected = plans[String(budget)]?.[modeKeys[mode]]
  if (!selected) return emptyOfficialPlan(budget, modeKeys[mode])
  if (selected.actual_cost > budget || selected.recommended_budget > budget) {
    return emptyOfficialPlan(budget, modeKeys[mode], '后台方案超出预算，已安全拒绝')
  }
  if (selected.decision === 'SKIP' && (selected.actual_cost !== 0 || selected.numbers.length !== 0)) {
    return emptyOfficialPlan(budget, modeKeys[mode], 'SKIP方案含有投注内容，已安全拒绝')
  }
  return selected
}
