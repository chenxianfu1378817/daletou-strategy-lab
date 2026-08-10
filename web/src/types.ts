export type NavigationKey = 'home' | 'backtest' | 'research' | 'bets' | 'validation'

export interface BacktestRow {
  model: string
  period: string
  tickets: number
  total_cost: number
  total_prize: number
  net_profit: number
  roi: number
  excess_roi: number
  max_drawdown: number
  profit_factor: number
  profitable_draw_rate: number
  longest_losing_streak: number
  largest_prize: number
  roi_excluding_largest: number
  roi_excluding_top_1pct: number
  non_jackpot_roi: number
  random_percentile: number
}

export interface AppData {
  version: string
  generatedAt: string
  source: string
  latest: {
    issue: string
    drawDate: string
    front: number[]
    back: number[]
    jackpotAfter?: number
    ruleVersion: string
    verified: boolean
  }
  history: { count: number; firstIssue: string; lastIssue: string }
  recommendation: {
    issue: string
    decision: 'BET' | 'SKIP'
    suggestedAmount: number
    budgetLimit: number
    mode: string
    betType: string
    reasons: string[]
    uncertainty: number
    researchNumbers: string[]
  }
  backtests: BacktestRow[]
  validation: Record<string, string>
}

