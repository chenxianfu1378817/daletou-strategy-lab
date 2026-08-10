export type ResearchPlan = {
  numbers: string[]
  estimatedCost: number
  atomicBets: number
  summary: string
}

type RandomSource = () => number

const ATOMIC_BET_COST = 2
const MAX_VISIBLE_SINGLE_LINES = 5

function combination(n: number, k: number): number {
  if (k < 0 || k > n) return 0
  let value = 1
  for (let index = 1; index <= k; index += 1) value = value * (n - index + 1) / index
  return value
}

export function expandedCost(frontCount: number, backCount: number): number {
  return combination(frontCount, 5) * combination(backCount, 2) * ATOMIC_BET_COST
}

function sampleDistinct(max: number, count: number, random: RandomSource): number[] {
  const pool = Array.from({ length: max }, (_, index) => index + 1)
  const selected: number[] = []
  for (let index = 0; index < count; index += 1) {
    const rawIndex = Math.floor(random() * pool.length)
    const poolIndex = Math.max(0, Math.min(pool.length - 1, rawIndex))
    selected.push(pool.splice(poolIndex, 1)[0])
  }
  return selected.sort((left, right) => left - right)
}

function formatLine(frontCount: number, backCount: number, random: RandomSource): string {
  const format = (value: number) => String(value).padStart(2, '0')
  const front = sampleDistinct(35, frontCount, random).map(format).join(' ')
  const back = sampleDistinct(12, backCount, random).map(format).join(' ')
  return `${front} + ${back}`
}

function singleLines(count: number, random: RandomSource): string[] {
  const result = new Set<string>()
  for (let attempts = 0; result.size < count && attempts < count * 30; attempts += 1) {
    result.add(formatLine(5, 2, random))
  }
  return [...result]
}

const compoundSizes = [
  [6, 4],
  [7, 2],
  [6, 3],
  [6, 2],
  [5, 3],
  [5, 2],
] as const

function bestCompound(budget: number): readonly [number, number] | undefined {
  return compoundSizes
    .filter(([front, back]) => expandedCost(front, back) <= budget)
    .sort((left, right) => expandedCost(right[0], right[1]) - expandedCost(left[0], left[1]))[0]
}

export function generateResearchPlan(mode: string, budget: number, random: RandomSource = Math.random): ResearchPlan {
  if (budget < ATOMIC_BET_COST) {
    return { numbers: [], estimatedCost: 0, atomicBets: 0, summary: '预算为 0，未生成投注方案。' }
  }

  if (mode === '复式') {
    const [frontCount, backCount] = bestCompound(budget) ?? [5, 2]
    const estimatedCost = expandedCost(frontCount, backCount)
    return {
      numbers: [formatLine(frontCount, backCount, random)],
      estimatedCost,
      atomicBets: estimatedCost / ATOMIC_BET_COST,
      summary: `已生成 1 组复式研究号码，展开 ${estimatedCost / ATOMIC_BET_COST} 注。`,
    }
  }

  if (mode === '混合') {
    const reservedForSingles = budget >= 6 ? 4 : 0
    const compound = bestCompound(budget - reservedForSingles)
    const numbers: string[] = []
    let estimatedCost = 0
    if (compound) {
      numbers.push(formatLine(compound[0], compound[1], random))
      estimatedCost += expandedCost(compound[0], compound[1])
    }
    const singleCount = Math.min(2, Math.floor((budget - estimatedCost) / ATOMIC_BET_COST))
    numbers.push(...singleLines(singleCount, random))
    estimatedCost += singleCount * ATOMIC_BET_COST
    return {
      numbers,
      estimatedCost,
      atomicBets: estimatedCost / ATOMIC_BET_COST,
      summary: `已生成复式与单式混合研究方案，共展开 ${estimatedCost / ATOMIC_BET_COST} 注。`,
    }
  }

  const count = Math.min(MAX_VISIBLE_SINGLE_LINES, Math.floor(budget / ATOMIC_BET_COST))
  const numbers = singleLines(count, random)
  const estimatedCost = numbers.length * ATOMIC_BET_COST
  return {
    numbers,
    estimatedCost,
    atomicBets: numbers.length,
    summary: mode === '智能推荐'
      ? `已生成 ${numbers.length} 组本地研究样本；当前 SKIP 结论不变。`
      : `已生成 ${numbers.length} 注单式研究号码。`,
  }
}
