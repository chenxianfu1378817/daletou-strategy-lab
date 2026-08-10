import type { CandidateComparison, OfficialPlan, RecommendationPlans } from './types'

export const modeKeys = {
  '智能推荐': 'Smart',
  '单式': 'Single',
  '复式': 'Multiple',
  '混合': 'Hybrid',
} as const

export type ModeLabel = keyof typeof modeKeys

export type CompoundCandidate = {
  numbers: string
  atomicBets: string[]
  cost: number
}

export type ResearchCandidate = {
  mode: string
  cost: number
  atomicBets: string[]
  compound: CompoundCandidate | null
  singles: string[]
}

const format = (value: number) => String(value).padStart(2, '0')

export function parseCandidateNumbers(numbers: string) {
  const [front, back] = numbers.split('+').map((part) => part.trim().split(/\s+/).map(Number))
  return { front, back }
}

function combination(n: number, k: number): number {
  if (k < 0 || k > n) return 0
  let value = 1
  for (let index = 1; index <= k; index += 1) value = value * (n - index + 1) / index
  return value
}

function combinations(values: number[], count: number): number[][] {
  if (count === 0) return [[]]
  const result: number[][] = []
  for (let index = 0; index <= values.length - count; index += 1) {
    for (const suffix of combinations(values.slice(index + 1), count - 1)) result.push([values[index], ...suffix])
  }
  return result
}

function formatNumbers(front: number[], back: number[]): string {
  return `${front.map(format).join(' ')} + ${back.map(format).join(' ')}`
}

function findCompoundPrefix(candidate: CandidateComparison): CompoundCandidate | null {
  let compound: CompoundCandidate | null = null
  for (let count = 1; count <= candidate.candidate_atomic_bets.length; count += 1) {
    const prefix = candidate.candidate_atomic_bets.slice(0, count)
    const parsed = prefix.map(parseCandidateNumbers)
    const front = [...new Set(parsed.flatMap((item) => item.front))].sort((left, right) => left - right)
    const back = [...new Set(parsed.flatMap((item) => item.back))].sort((left, right) => left - right)
    if (combination(front.length, 5) * combination(back.length, 2) !== count) continue
    const expanded = new Set(combinations(front, 5).flatMap((frontPart) => combinations(back, 2).map((backPart) => formatNumbers(frontPart, backPart))))
    if (expanded.size !== count || prefix.some((numbers) => !expanded.has(numbers))) continue
    const unitCost = candidate.candidate_atomic_bets.length ? candidate.candidate_cost / candidate.candidate_atomic_bets.length : 0
    compound = { numbers: formatNumbers(front, back), atomicBets: prefix, cost: count * unitCost }
  }
  return compound
}

export function selectResearchCandidate(plan: OfficialPlan): ResearchCandidate | null {
  const wanted = plan.mode === 'Smart' ? plan.selected_candidate : plan.mode
  const candidate = plan.comparisons.find((item) => item.mode === wanted)
  if (!candidate) return null
  if (candidate.mode === 'Single') {
    return { mode: candidate.mode, cost: candidate.candidate_cost, atomicBets: candidate.candidate_atomic_bets, compound: null, singles: candidate.candidate_atomic_bets }
  }
  const compound = findCompoundPrefix(candidate)
  return {
    mode: candidate.mode,
    cost: candidate.candidate_cost,
    atomicBets: candidate.candidate_atomic_bets,
    compound,
    singles: compound ? candidate.candidate_atomic_bets.slice(compound.atomicBets.length) : candidate.candidate_atomic_bets,
  }
}

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
