const modeLabels: Record<string, string> = {
  Smart: '智能推荐',
  Single: '单式',
  Multiple: '复式',
  Hybrid: '混合',
}

const modelLabels: Record<string, string> = {
  Random: '随机基准',
  RandomCoverage: '随机覆盖基准',
  'Random + Coverage': '随机覆盖基准',
  'Current Model': '当前模型',
  'Current Model + Coverage': '当前模型 + 组合覆盖',
  'Current Model + Coverage + Bet/Skip': '当前模型 + 组合覆盖 + 投注/跳过判断',
  'Current Model + Coverage + Bet/Skip + Budget/Smart': '当前模型 + 组合覆盖 + 投注/跳过判断 + 预算/智能推荐',
  Frequency: '频率模型',
  Bayesian: '贝叶斯模型',
  Ensemble: '集成模型',
}

const evidenceLabels: Record<string, string> = {
  INSUFFICIENT: '证据不足',
  VALID: '证据有效',
  STALE: '证据已过期',
  INVALID: '证据异常',
}

export const modeLabel = (value: string | null) => value ? (modeLabels[value] ?? value) : '无'
export const modelLabel = (value: string) => modelLabels[value] ?? value
export const evidenceStatusLabel = (value: string) => evidenceLabels[value] ?? value
export const decisionLabel = (value: 'BET' | 'SKIP') => value === 'BET' ? '建议投注' : '建议不投注'

export function translateVisibleText(value: string): string {
  return value
    .replaceAll('LOCKED_UNEVALUATED', '已封存，尚未验收')
    .replaceAll('EVALUATED_PASS', '已验收通过')
    .replaceAll('EVALUATED_FAIL', '已验收未通过')
    .replaceAll('Locked Holdout', '封存测试')
    .replaceAll('Forward Paper Test', '前向虚拟验证')
    .replaceAll('Forward Paper', '前向虚拟验证')
    .replaceAll('Holdout', '封存测试')
    .replaceAll('Evidence', '策略证据')
    .replaceAll('INSUFFICIENT', '证据不足')
    .replaceAll('INVALID', '证据异常')
    .replaceAll('STALE', '证据已过期')
    .replaceAll('VALID', '证据有效')
    .replaceAll('Single', '单式')
    .replaceAll('Multiple', '复式')
    .replaceAll('Hybrid', '混合')
    .replaceAll('Smart', '智能推荐')
    .replaceAll('BET', '建议投注')
    .replaceAll('SKIP', '建议不投注')
}
