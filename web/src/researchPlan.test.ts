import { describe, expect, it } from 'vitest'
import { expandedCost, generateResearchPlan } from './researchPlan'

function seededRandom(seed = 17) {
  return () => {
    seed = (seed * 16807) % 2147483647
    return (seed - 1) / 2147483646
  }
}

function parseLine(line: string) {
  const [front, back] = line.split('+').map((part) => part.trim().split(/\s+/).map(Number))
  return { front, back }
}

describe('research plan generation', () => {
  it('generates valid, unique and sorted single lines', () => {
    const plan = generateResearchPlan('单式', 20, seededRandom())
    expect(plan.numbers).toHaveLength(5)
    for (const line of plan.numbers) {
      const { front, back } = parseLine(line)
      expect(front).toEqual([...new Set(front)].sort((a, b) => a - b))
      expect(back).toEqual([...new Set(back)].sort((a, b) => a - b))
      expect(front).toHaveLength(5)
      expect(back).toHaveLength(2)
      expect(front.every((value) => value >= 1 && value <= 35)).toBe(true)
      expect(back.every((value) => value >= 1 && value <= 12)).toBe(true)
    }
  })

  it('keeps compound and mixed plans within the selected budget', () => {
    for (const mode of ['复式', '混合']) {
      const plan = generateResearchPlan(mode, 20, seededRandom())
      expect(plan.estimatedCost).toBeLessThanOrEqual(20)
      expect(plan.numbers.length).toBeGreaterThan(0)
    }
  })

  it('uses the official atomic expansion cost', () => {
    expect(expandedCost(5, 2)).toBe(2)
    expect(expandedCost(6, 3)).toBe(36)
  })

  it('does not generate a plan for a zero budget', () => {
    expect(generateResearchPlan('智能推荐', 0, seededRandom())).toMatchObject({
      numbers: [], estimatedCost: 0, atomicBets: 0,
    })
  })
})
