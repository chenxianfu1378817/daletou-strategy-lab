import { Check, Clipboard, Info, LockKeyhole, RefreshCcw } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import type { AppData } from '../types'
import { dateTime, money } from '../utils'
import { Balls } from '../components/Balls'
import { generateResearchPlan, type ResearchPlan } from '../researchPlan'

const budgets = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100]
const modes = ['智能推荐', '单式', '复式', '混合']
const defaultResearchNumbers = ['03 11 18 24 33 + 04 09']

type Props = { data: AppData; stale: boolean; fallback: boolean }

export function HomePage({ data, stale, fallback }: Props) {
  const [budget, setBudget] = useState(100)
  const [mode, setMode] = useState('智能推荐')
  const [generatedPlan, setGeneratedPlan] = useState<ResearchPlan | null>(null)
  const [generationCount, setGenerationCount] = useState(0)
  const [copied, setCopied] = useState(false)
  const researchSectionRef = useRef<HTMLElement>(null)
  const recommendation = data.recommendation
  const researchNumbers = recommendation.researchNumbers.length ? recommendation.researchNumbers : defaultResearchNumbers
  const displayedNumbers = generatedPlan?.numbers ?? researchNumbers
  const copyText = useMemo(() => displayedNumbers.join('\n'), [displayedNumbers])

  function chooseBudget(value: number) {
    setBudget(value)
    setGeneratedPlan(null)
  }

  function chooseMode(value: string) {
    setMode(value)
    setGeneratedPlan(null)
  }

  function generatePlan() {
    setGeneratedPlan(generateResearchPlan(mode, budget))
    setGenerationCount((count) => count + 1)
    setCopied(false)
    window.requestAnimationFrame(() => researchSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  async function copyNumbers() {
    await navigator.clipboard.writeText(copyText)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <div className="page home-page">
      {(stale || fallback) && <div className="stale-warning" role="alert">数据可能已过期：当前展示最后一份已验证快照，不会伪装成最新推荐。</div>}
      <section className="latest-band" aria-labelledby="latest-title">
        <div className="latest-issue">
          <span id="latest-title">最新期号</span>
          <strong>{data.latest.issue}</strong>
        </div>
        <div className="latest-numbers">
          <span>开奖号码</span>
          <Balls front={data.latest.front} back={data.latest.back} />
        </div>
        <div className="latest-meta">
          <span>最后更新：{dateTime(data.generatedAt)}</span>
          <span className="status-ok"><i />数据状态：{data.latest.verified ? '已验证' : '待核验'}</span>
          <span>规则：{data.latest.ruleVersion}</span>
        </div>
      </section>

      <section className="decision-band" aria-labelledby="decision-title">
        <div className="decision-main">
          <span id="decision-title">本期建议</span>
          <strong className={recommendation.decision === 'SKIP' ? 'decision-skip' : 'decision-bet'}>{recommendation.decision}</strong>
        </div>
        <div><span>建议金额</span><strong>{money(recommendation.suggestedAmount)}</strong></div>
        <div><span>预算上限</span><strong>{money(budget)}</strong></div>
        <div><span>推荐模式</span><strong className="accent-text">{mode}</strong></div>
        <p>在 {budget} 元预算内，当前数据未显示统计意义上的稳定正期望优势，建议跳过本期。</p>
      </section>

      <section className="control-section">
        <div className="section-heading"><h2>预算上限（元）</h2><p>用户预算是上限，不是必须花完的目标</p></div>
        <div className="budget-grid" role="group" aria-label="预算上限">
          {budgets.map((value) => (
            <button className={budget === value ? 'is-selected' : ''} onClick={() => chooseBudget(value)} key={value} aria-pressed={budget === value}>
              {value}{budget === value && <Check size={14} aria-hidden="true" />}
            </button>
          ))}
        </div>
        <p className="helper">所有单式、复式、混合与追加方案均按 Atomic Bets 展开后校验成本。</p>
      </section>

      <section className="control-section">
        <div className="section-heading"><h2>推荐模式</h2><p>不同模式只改变组合结构，不改变摇号概率</p></div>
        <div className="mode-control" role="group" aria-label="推荐模式">
          {modes.map((value) => <button className={mode === value ? 'is-selected' : ''} onClick={() => chooseMode(value)} key={value}>{value}</button>)}
        </div>
        <button className="primary-action" onClick={generatePlan}>生成本期方案</button>
        <p className="research-lock"><LockKeyhole size={16} />生成结果用于研究；是否建议购买由 Bet/Skip 证据阈值决定。</p>
      </section>

      <section className="reason-section">
        <h2><Info size={20} />本期推荐理由</h2>
        <ul>
          {recommendation.reasons.map((reason) => <li key={reason}>{reason}</li>)}
          <li>模型不确定性 {(recommendation.uncertainty * 100).toFixed(0)}%，预算不会因连续未中奖而提高。</li>
        </ul>
        <p>以上结论只使用开奖前可获得的数据与预先登记的模型版本；不读取目标期或未来期数据。</p>
      </section>

      <section className={`research-number-section ${generatedPlan ? 'is-generated' : ''}`} ref={researchSectionRef}>
        <div className="research-title">
          <h2>研究用虚拟号码 <em>（不建议实际购买）</em></h2>
          <div>
            <button onClick={copyNumbers} disabled={displayedNumbers.length === 0}>{copied ? <Check size={16} /> : <Clipboard size={16} />}{copied ? '已复制' : '复制'}</button>
            <button onClick={generatePlan}><RefreshCcw size={16} />换一组</button>
          </div>
        </div>
        {generatedPlan && (
          <div className="generation-feedback" role="status" aria-live="polite" key={generationCount}>
            <strong>{generatedPlan.summary}</strong>
            <span>理论金额 {money(generatedPlan.estimatedCost)}，不超过所选预算 {money(budget)}。</span>
          </div>
        )}
        {displayedNumbers.map((numbers) => {
          const [front, back] = numbers.split('+').map((part) => part.trim().split(/\s+/).map(Number))
          return <Balls front={front} back={back} size="sm" key={`${generationCount}-${numbers}`} />
        })}
        {generatedPlan && displayedNumbers.length === 0 && <div className="empty-plan">预算为 0，未生成号码。</div>}
        <p>仅用于研究与回测示例，不构成购彩建议或收益承诺。</p>
      </section>
    </div>
  )
}
