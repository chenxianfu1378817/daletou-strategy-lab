import type { AppData } from './types'

export const fallbackData: AppData = {
  version: '1.0.0',
  generatedAt: '2026-08-10T00:00:00Z',
  source: 'China Sports Lottery official gateway',
  latest: {
    issue: '26089',
    drawDate: '2026-08-08',
    front: [3, 7, 12, 14, 26],
    back: [5, 11],
    jackpotAfter: 817996545.38,
    ruleVersion: 'rule_2026_26014',
    verified: true,
  },
  history: { count: 0, firstIssue: '—', lastIssue: '26089' },
  recommendation: {
    issue: '26090',
    decision: 'SKIP',
    suggestedAmount: 0,
    budgetLimit: 100,
    mode: '智能推荐',
    betType: '不投注',
    reasons: ['当前策略无显著样本外优势', '尚未超过随机策略高分位', 'Forward Paper 样本仍不足'],
    uncertainty: 0.78,
    researchNumbers: ['03 11 18 24 33 + 04 09'],
  },
  backtests: [],
  validation: { training: 'complete', validation: 'complete', holdout: 'locked', forward: 'collecting' },
}

export async function loadData(): Promise<{ data: AppData; fallback: boolean }> {
  try {
    const response = await fetch('./data/app-data.json', { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return { data: (await response.json()) as AppData, fallback: false }
  } catch {
    return { data: fallbackData, fallback: true }
  }
}

export function isStale(isoDate: string, now = new Date()): boolean {
  const generated = new Date(isoDate)
  return Number.isNaN(generated.getTime()) || now.getTime() - generated.getTime() > 5 * 24 * 60 * 60 * 1000
}

