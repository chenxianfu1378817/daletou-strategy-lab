import { describe, expect, it } from 'vitest'
import type { OfficialPlan, RecommendationPlans } from './types'
import { selectOfficialPlan, selectResearchCandidate } from './researchPlan'

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

describe('backend research candidate presentation', () => {
  const compoundAtoms = [
    '01 02 03 04 05 + 01 02', '01 02 03 04 06 + 01 02', '01 02 03 05 06 + 01 02',
    '01 02 04 05 06 + 01 02', '01 03 04 05 06 + 01 02', '02 03 04 05 06 + 01 02',
  ]
  const extraSingles = ['07 08 09 10 11 + 03 04', '12 13 14 15 16 + 05 06']

  it('shows every backend single candidate', () => {
    const single = { ...plan, decision: 'SKIP' as const, recommended_budget: 0, actual_cost: 0, numbers: [], selected_candidate: 'Single', comparisons: [{ mode: 'Single', score: 0, meets_bet_standard: false, metrics: {}, candidate_cost: 4, candidate_atomic_bets: extraSingles, official: false }] }
    expect(selectResearchCandidate(single)).toMatchObject({ mode: 'Single', cost: 4, singles: extraSingles })
  })

  it('reconstructs the backend multiple without generating numbers', () => {
    const multiple = { ...plan, decision: 'SKIP' as const, recommended_budget: 0, actual_cost: 0, mode: 'Multiple', numbers: [], selected_candidate: 'Multiple', comparisons: [{ mode: 'Multiple', score: 0, meets_bet_standard: false, metrics: {}, candidate_cost: 12, candidate_atomic_bets: compoundAtoms, official: false }] }
    const candidate = selectResearchCandidate(multiple)
    expect(candidate?.compound).toMatchObject({ numbers: '01 02 03 04 05 06 + 01 02', cost: 12, atomicBets: compoundAtoms })
    expect(candidate?.singles).toEqual([])
  })

  it('splits the backend hybrid into compound and single parts', () => {
    const hybridAtoms = [...compoundAtoms, ...extraSingles]
    const hybrid = { ...plan, decision: 'SKIP' as const, recommended_budget: 0, actual_cost: 0, mode: 'Smart', numbers: [], selected_candidate: 'Hybrid', comparisons: [{ mode: 'Hybrid', score: 0, meets_bet_standard: false, metrics: {}, candidate_cost: 16, candidate_atomic_bets: hybridAtoms, official: false }] }
    const candidate = selectResearchCandidate(hybrid)
    expect(candidate?.compound?.atomicBets).toEqual(compoundAtoms)
    expect(candidate?.compound?.cost).toBe(12)
    expect(candidate?.singles).toEqual(extraSingles)
    expect(candidate?.atomicBets).toEqual(hybridAtoms)
  })
})
