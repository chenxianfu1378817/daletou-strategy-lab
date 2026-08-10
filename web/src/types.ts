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

export interface CandidateComparison {
  mode: string
  score: number
  meets_bet_standard: boolean
  metrics: Record<string, number | string>
  candidate_cost: number
  candidate_atomic_bets: string[]
  official: boolean
}

export interface OfficialPlan {
  decision: 'BET' | 'SKIP'
  budget_limit: number
  recommended_budget: number
  mode: string
  bet_type: string
  numbers: string[]
  atomic_bets: string[]
  atomic_bet_count: number
  actual_cost: number
  unused_budget: number
  reasons: string[]
  bet_score: number
  selected_candidate: string | null
  comparisons: CandidateComparison[]
}

export type RecommendationPlans = Record<string, Partial<Record<'Smart' | 'Single' | 'Multiple' | 'Hybrid', OfficialPlan>>>

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
    numbers: string[]
    evidence: {
      status: string
      bet_eligible: boolean
      source_issue: string
      walk_forward_roi: number | null
      excess_roi_vs_random: number | null
      random_percentile: number | null
      maximum_drawdown: number | null
      roi_excluding_largest_win: number | null
      validation_status: string
      holdout_status: string
      forward_periods: number
      forward_roi: number | null
      model_stability: number | null
      random_seed_count: number
      problems: string[]
    }
    plans: RecommendationPlans
    modelVersion: string
    strategyVersion: string
    randomSeed: number
    gitCommitHash: string
    immutableHash: string
    officialNumbersSource: string
  }
  backtests: BacktestRow[]
  validation: Record<string, string>
}
