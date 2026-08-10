import { Check, Clipboard, Info, LockKeyhole } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import type { AppData, OfficialPlan } from '../types'
import { dateTime, money } from '../utils'
import { Balls } from '../components/Balls'
import { selectOfficialPlan, type ModeLabel } from '../researchPlan'

const budgets = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100]
const modes: ModeLabel[] = ['智能推荐', '单式', '复式', '混合']

type Props = { data: AppData; stale: boolean; fallback: boolean }

export function HomePage({ data, stale, fallback }: Props) {
  const [budget, setBudget] = useState(100)
  const [mode, setMode] = useState<ModeLabel>('智能推荐')
  const [generatedPlan, setGeneratedPlan] = useState<OfficialPlan | null>(null)
  const [copied, setCopied] = useState(false)
  const resultRef = useRef<HTMLElement>(null)
  const recommendation = data.recommendation
  const displayedPlan = generatedPlan ?? selectOfficialPlan(recommendation.plans, budget, mode)
  const copyText = useMemo(() => displayedPlan.numbers.join('\n'), [displayedPlan.numbers])
  const evidenceUnsafe = stale || fallback || recommendation.evidence.status === 'STALE' || recommendation.evidence.status === 'INVALID'

  function chooseBudget(value: number) {
    setBudget(value)
    setGeneratedPlan(null)
  }

  function chooseMode(value: ModeLabel) {
    setMode(value)
    setGeneratedPlan(null)
  }

  function generatePlan() {
    const plan = evidenceUnsafe
      ? { ...selectOfficialPlan({}, budget, mode), reasons: ['Evidence缺失或过期，不生成假推荐'] }
      : selectOfficialPlan(recommendation.plans, budget, mode)
    setGeneratedPlan(plan)
    setCopied(false)
    window.requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  async function copyNumbers() {
    if (!copyText) return
    await navigator.clipboard.writeText(copyText)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <div className="page home-page">
      {(stale || fallback) && <div className="stale-warning" role="alert">数据可能已过期：系统已锁定SKIP / 0元，不会生成假推荐。</div>}
      <section className="latest-band" aria-labelledby="latest-title">
        <div className="latest-issue"><span id="latest-title">最新期号</span><strong>{data.latest.issue}</strong></div>
        <div className="latest-numbers"><span>开奖号码</span><Balls front={data.latest.front} back={data.latest.back} /></div>
        <div className="latest-meta">
          <span>最后更新：{dateTime(data.generatedAt)}</span>
          <span className="status-ok"><i />数据状态：{data.latest.verified ? '已验证' : '待核验'}</span>
          <span>规则：{data.latest.ruleVersion}</span>
        </div>
      </section>

      <section className="decision-band" aria-labelledby="decision-title">
        <div className="decision-main"><span id="decision-title">本期建议</span><strong className={displayedPlan.decision === 'SKIP' ? 'decision-skip' : 'decision-bet'}>{displayedPlan.decision}</strong></div>
        <div><span>建议金额</span><strong>{money(displayedPlan.recommended_budget)}</strong></div>
        <div><span>预算上限</span><strong>{money(budget)}</strong></div>
        <div><span>推荐模式</span><strong className="accent-text">{mode}</strong></div>
        <p>{displayedPlan.decision === 'SKIP' ? '真实Evidence未达BET阈值，本期正式推荐为0元。' : `后台策略推荐 ${money(displayedPlan.actual_cost)}，不超过所选预算。`}</p>
      </section>

      <section className="control-section">
        <div className="section-heading"><h2>预算上限（元）</h2><p>用户预算是上限，不是必须花完的目标</p></div>
        <div className="budget-grid" role="group" aria-label="预算上限">{budgets.map((value) => (
          <button className={budget === value ? 'is-selected' : ''} onClick={() => chooseBudget(value)} key={value} aria-pressed={budget === value}>{value}{budget === value && <Check size={14} />}</button>
        ))}</div>
        <p className="helper">所有Single、Multiple、Hybrid都在Python后台展开为Atomic Bets后比较。</p>
      </section>

      <section className="control-section">
        <div className="section-heading"><h2>推荐模式</h2><p>Smart比较三类候选的真实指标</p></div>
        <div className="mode-control" role="group" aria-label="推荐模式">{modes.map((value) => <button className={mode === value ? 'is-selected' : ''} onClick={() => chooseMode(value)} key={value}>{value}</button>)}</div>
        <button className="primary-action" onClick={generatePlan}>生成本期方案</button>
        <p className="research-lock"><LockKeyhole size={16} />正式号码仅来自 recommendation.json；前端不执行选号。</p>
      </section>

      <section className="reason-section">
        <h2><Info size={20} />Evidence状态：{recommendation.evidence.status}</h2>
        <ul>{displayedPlan.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
        <p>Walk-forward ROI：{recommendation.evidence.walk_forward_roi == null ? '缺失' : `${(recommendation.evidence.walk_forward_roi * 100).toFixed(1)}%`}；Random seeds：{recommendation.evidence.random_seed_count}；Forward：{recommendation.evidence.forward_periods}期；Holdout：{recommendation.evidence.holdout_status}。</p>
      </section>

      <section className={`research-number-section ${generatedPlan ? 'is-generated' : ''}`} ref={resultRef}>
        <div className="research-title"><h2>正式投注方案</h2><button onClick={copyNumbers} disabled={displayedPlan.numbers.length === 0}>{copied ? <Check size={16} /> : <Clipboard size={16} />}{copied ? '已复制' : '复制全部号码'}</button></div>
        <div className="generation-feedback" role="status" aria-live="polite">
          <strong>{displayedPlan.decision === 'SKIP' ? 'SKIP / 0元：本期没有正式投注号码。' : `共 ${displayedPlan.atomic_bet_count} 注，实际 ${money(displayedPlan.actual_cost)}。`}</strong>
          <span>后台选中候选：{displayedPlan.selected_candidate ?? '无'}</span>
        </div>
        {displayedPlan.numbers.map((numbers) => {
          const [front, back] = numbers.split('+').map((part) => part.trim().split(/\s+/).map(Number))
          return <Balls front={front} back={back} size="sm" key={numbers} />
        })}
        {displayedPlan.numbers.length === 0 && <div className="empty-plan">无正式号码。系统不会在Evidence不足时用随机号码填充。</div>}
        <p>版本 {recommendation.strategyVersion} · {recommendation.modelVersion} · 证据源期 {recommendation.evidence.source_issue}</p>
      </section>
    </div>
  )
}
