import { Check, Clipboard, Info, LockKeyhole } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import type { AppData, OfficialPlan } from '../types'
import { dateTime, money } from '../utils'
import { Balls } from '../components/Balls'
import { parseCandidateNumbers, selectOfficialPlan, selectResearchCandidate, type ModeLabel } from '../researchPlan'
import { decisionLabel, evidenceStatusLabel, modeLabel, translateVisibleText } from '../labels'

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
  const researchCandidate = generatedPlan ? selectResearchCandidate(generatedPlan) : null
  const copyLines = displayedPlan.numbers.length ? displayedPlan.numbers : (researchCandidate?.atomicBets ?? [])
  const copyText = useMemo(() => copyLines.join('\n'), [copyLines])
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
      ? { ...selectOfficialPlan({}, budget, mode), reasons: ['策略证据缺失或过期，不生成假推荐'] }
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
      {(stale || fallback) && <div className="stale-warning" role="alert">数据可能已过期：系统已锁定“建议不投注 / 0元”，不会生成假推荐。</div>}
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
        <div className="decision-main"><span id="decision-title">本期建议</span><strong className={displayedPlan.decision === 'SKIP' ? 'decision-skip' : 'decision-bet'}>{decisionLabel(displayedPlan.decision)}</strong></div>
        <div><span>建议金额</span><strong>{money(displayedPlan.recommended_budget)}</strong></div>
        <div><span>预算上限</span><strong>{money(budget)}</strong></div>
        <div><span>推荐模式</span><strong className="accent-text">{mode}</strong></div>
        <p>{displayedPlan.decision === 'SKIP' ? '真实策略证据未达建议投注阈值，本期正式建议为0元。' : `后台策略推荐 ${money(displayedPlan.actual_cost)}，不超过所选预算。`}</p>
      </section>

      <section className="control-section">
        <div className="section-heading"><h2>预算上限（元）</h2><p>用户预算是上限，不是必须花完的目标</p></div>
        <div className="budget-grid" role="group" aria-label="预算上限">{budgets.map((value) => (
          <button className={budget === value ? 'is-selected' : ''} onClick={() => chooseBudget(value)} key={value} aria-pressed={budget === value}>{value}{budget === value && <Check size={14} />}</button>
        ))}</div>
        <p className="helper">所有单式、复式、混合方案都在Python后台展开为原子注后比较。</p>
      </section>

      <section className="control-section">
        <div className="section-heading"><h2>推荐模式</h2><p>智能推荐比较三类候选的真实指标</p></div>
        <div className="mode-control" role="group" aria-label="推荐模式">{modes.map((value) => <button className={mode === value ? 'is-selected' : ''} onClick={() => chooseMode(value)} key={value}>{value}</button>)}</div>
        <button className="primary-action" onClick={generatePlan}>生成本期方案</button>
        <p className="research-lock"><LockKeyhole size={16} />正式号码与模型研究候选均来自后台 recommendation.json；前端不执行选号。</p>
      </section>

      <section className="reason-section">
        <h2><Info size={20} />策略证据状态：{evidenceStatusLabel(recommendation.evidence.status)}</h2>
        <ul>{displayedPlan.reasons.map((reason) => <li key={reason}>{translateVisibleText(reason)}</li>)}</ul>
        <p>逐期前推投资回报率（ROI）：{recommendation.evidence.walk_forward_roi == null ? '缺失' : `${(recommendation.evidence.walk_forward_roi * 100).toFixed(1)}%`}；随机基准种子：{recommendation.evidence.random_seed_count}；前向虚拟验证：{recommendation.evidence.forward_periods}期；封存测试：{translateVisibleText(recommendation.evidence.holdout_status)}。</p>
      </section>

      <section className={`research-number-section ${generatedPlan ? 'is-generated' : ''}`} ref={resultRef}>
        <div className="research-title"><h2>正式投注结论</h2></div>
        <div className="generation-feedback" role="status" aria-live="polite">
          <strong>{displayedPlan.decision === 'SKIP' ? '建议不投注 / 0元：本期没有正式投注号码。' : `共 ${displayedPlan.atomic_bet_count} 注，实际 ${money(displayedPlan.actual_cost)}。`}</strong>
          <span>后台选中候选：{modeLabel(displayedPlan.selected_candidate)}</span>
        </div>
        {displayedPlan.numbers.map((numbers) => {
          const [front, back] = numbers.split('+').map((part) => part.trim().split(/\s+/).map(Number))
          return <Balls front={front} back={back} size="sm" key={numbers} />
        })}
        {displayedPlan.numbers.length === 0 && <div className="empty-plan">无正式号码。系统不会在策略证据不足时用随机号码填充。</div>}

        {generatedPlan && researchCandidate && (
          <div className="model-candidate">
            <div className="research-title">
              <div><h2>模型研究候选 · {modeLabel(generatedPlan.mode)}{generatedPlan.mode === 'Smart' ? `（选中：${modeLabel(researchCandidate.mode)}）` : ''}</h2><span>候选金额 {money(researchCandidate.cost)} · 展开 {researchCandidate.atomicBets.length} 注原子注</span></div>
              <button onClick={copyNumbers} disabled={copyLines.length === 0}>{copied ? <Check size={16} /> : <Clipboard size={16} />}{copied ? '已复制' : '复制候选号码'}</button>
            </div>
            <p className="candidate-disclaimer">仅供模型研究和前向验证，当前不属于正式投注建议。</p>
            {researchCandidate.compound && (
              <div className="candidate-group">
                <h3>{researchCandidate.mode === 'Hybrid' ? '复式部分' : '复式号码'}<span>实际金额 {money(researchCandidate.compound.cost)} · 展开 {researchCandidate.compound.atomicBets.length} 注</span></h3>
                <Balls {...parseCandidateNumbers(researchCandidate.compound.numbers)} size="sm" />
              </div>
            )}
            {researchCandidate.singles.length > 0 && (
              <div className="candidate-group">
                <h3>{researchCandidate.mode === 'Multiple' ? '复式展开原子注' : researchCandidate.mode === 'Hybrid' ? '单式部分' : '单式候选'}<span>共 {researchCandidate.singles.length} 注</span></h3>
                {researchCandidate.singles.map((numbers) => <Balls {...parseCandidateNumbers(numbers)} size="sm" key={numbers} />)}
              </div>
            )}
          </div>
        )}
        {generatedPlan && !researchCandidate && <div className="empty-plan">当前预算没有后台模型研究候选。</div>}
        <p>版本 {recommendation.strategyVersion} · {recommendation.modelVersion} · 证据源期 {recommendation.evidence.source_issue}</p>
      </section>
    </div>
  )
}
