import { describe, expect, it } from 'vitest'
import type { OfficialPlan, RecommendationPlans } from './types'
import { selectOfficialPlan } from './researchPlan'

const plan: OfficialPlan = {
  decision: 'BET', budget_limit: 20, recommended_budget: 2, mode: 'Single', bet_type: '单式',
  numbers: ['01 02 03 04 05 + 01 02'], atomic_bets: ['01 02 03 04 05 + 01 02'],
  atomic_bet_count: 1, actual_cost: 2, unused_budget: 18, reasons: ['saved evidence'], bet_score: .8,
  selected_candidate: 'Single', comparisons: [],
}

describe('official recommendation selection', () => {
  it('returns the exact backend plan without generating numbers', () => {
    const plans: RecommendationPlans = { '20': { Single: plan } }
    expect(selectOfficialPlan(plans, 20, '单式')).toBe(plan)
    expect(selectOfficialPlan(plans, 20, '单式').numbers).toEqual(plan.numbers)
  })

  it('fails closed when a backend plan is missing', () => {
    expect(selectOfficialPlan({}, 20, '智能推荐')).toMatchObject({ decision: 'SKIP', actual_cost: 0, numbers: [] })
  })

  it('rejects an over-budget backend plan', () => {
    const plans: RecommendationPlans = { '20': { Single: { ...plan, actual_cost: 22, recommended_budget: 22 } } }
    expect(selectOfficialPlan(plans, 20, '单式')).toMatchObject({ decision: 'SKIP', actual_cost: 0 })
  })
})
