import { describe, expect, it } from 'vitest'
import { fallbackData, isStale } from './data'

describe('web data safety', () => {
  it('marks old snapshots as stale', () => {
    expect(isStale('2026-01-01T00:00:00Z', new Date('2026-08-10T00:00:00Z'))).toBe(true)
  })
  it('does not mark a fresh snapshot stale', () => {
    expect(isStale('2026-08-09T00:00:00Z', new Date('2026-08-10T00:00:00Z'))).toBe(false)
  })
  it('fallback recommendation is conservative', () => {
    expect(fallbackData.recommendation.decision).toBe('SKIP')
    expect(fallbackData.recommendation.suggestedAmount).toBe(0)
    expect(fallbackData.recommendation.numbers).toEqual([])
    expect(fallbackData.recommendation.evidence.status).toBe('INVALID')
  })
})
