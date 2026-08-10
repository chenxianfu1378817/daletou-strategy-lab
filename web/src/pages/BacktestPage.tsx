import { useMemo, useState } from 'react'
import type { AppData, BacktestRow } from '../types'
import { money, percent } from '../utils'
import { MetricStrip } from '../components/MetricStrip'
import { modelLabel } from '../labels'

const demoRows: BacktestRow[] = [
  { model: 'Random', period: '最近300期', tickets: 3000, total_cost: 6000, total_prize: 3020, net_profit: -2980, roi: -0.497, excess_roi: 0, max_drawdown: 3110, profit_factor: .51, profitable_draw_rate: .086, longest_losing_streak: 31, largest_prize: 300, roi_excluding_largest: -.547, roi_excluding_top_1pct: -.62, non_jackpot_roi: -.547, random_percentile: .5 },
  { model: 'RandomCoverage', period: '最近300期', tickets: 3000, total_cost: 6000, total_prize: 3195, net_profit: -2805, roi: -.468, excess_roi: .029, max_drawdown: 2920, profit_factor: .55, profitable_draw_rate: .093, longest_losing_streak: 28, largest_prize: 300, roi_excluding_largest: -.518, roi_excluding_top_1pct: -.59, non_jackpot_roi: -.518, random_percentile: .64 },
  { model: 'Frequency', period: '最近300期', tickets: 3000, total_cost: 6000, total_prize: 2880, net_profit: -3120, roi: -.52, excess_roi: -.023, max_drawdown: 3260, profit_factor: .47, profitable_draw_rate: .08, longest_losing_streak: 35, largest_prize: 300, roi_excluding_largest: -.57, roi_excluding_top_1pct: -.64, non_jackpot_roi: -.57, random_percentile: .38 },
  { model: 'Bayesian', period: '最近300期', tickets: 3000, total_cost: 6000, total_prize: 3270, net_profit: -2730, roi: -.455, excess_roi: .042, max_drawdown: 2860, profit_factor: .57, profitable_draw_rate: .097, longest_losing_streak: 27, largest_prize: 300, roi_excluding_largest: -.505, roi_excluding_top_1pct: -.58, non_jackpot_roi: -.505, random_percentile: .71 },
  { model: 'Ensemble', period: '最近300期', tickets: 3000, total_cost: 6000, total_prize: 3405, net_profit: -2595, roi: -.433, excess_roi: .064, max_drawdown: 2710, profit_factor: .6, profitable_draw_rate: .103, longest_losing_streak: 25, largest_prize: 300, roi_excluding_largest: -.483, roi_excluding_top_1pct: -.56, non_jackpot_roi: -.483, random_percentile: .79 },
]

export function BacktestPage({ data }: { data: AppData }) {
  const rows = data.backtests.length ? data.backtests : demoRows
  const [model, setModel] = useState('Current Model + Coverage')
  const [windowSize, setWindowSize] = useState('300')
  const [budget, setBudget] = useState('20')
  const [running, setRunning] = useState(false)
  const windowRows = useMemo(() => rows.filter((row) => row.period === `最近${windowSize}期`), [rows, windowSize])
  const models = useMemo(() => [...new Set(rows.map((row) => row.model))], [rows])
  const selected = useMemo(() => windowRows.find((row) => row.model === model) ?? windowRows[windowRows.length - 1] ?? rows[rows.length - 1], [model, rows, windowRows])

  function run() {
    setRunning(true)
    window.setTimeout(() => setRunning(false), 500)
  }

  return (
    <div className="page data-page">
      <header className="page-title"><div><h1>严格回测</h1><p>逐期前推 · 同预算原子注公平比较 · 不触碰封存测试</p></div><span>普通页面不开放封存测试调参</span></header>
      <section className="filter-rail">
        <label>模型<select value={model} onChange={(event) => setModel(event.target.value)}>{models.map((name) => <option value={name} key={name}>{modelLabel(name)}</option>)}</select></label>
        <label>区间<select value={windowSize} onChange={(event) => setWindowSize(event.target.value)}>{[100, 300, 500].map((n) => <option value={n} key={n}>最近{n}期</option>)}</select></label>
        <label>每期预算<select value={budget} onChange={(event) => setBudget(event.target.value)}>{[20, 40, 60, 80, 100].map((n) => <option key={n}>{n}</option>)}</select></label>
        <button onClick={run}>{running ? '计算中…' : '运行回测'}</button>
      </section>
      <MetricStrip metrics={[
        { label: '总投入', value: money(selected.total_cost) },
        { label: '总奖金', value: money(selected.total_prize) },
        { label: '净利润', value: money(selected.net_profit), tone: selected.net_profit < 0 ? 'negative' : 'positive' },
        { label: '投资回报率（ROI）', value: percent(selected.roi), tone: selected.roi < 0 ? 'negative' : 'positive' },
        { label: '相对随机超额ROI', value: percent(selected.excess_roi), tone: selected.excess_roi < 0 ? 'negative' : 'positive' },
        { label: '最大回撤', value: money(-selected.max_drawdown), tone: 'negative' },
        { label: '随机基准百分位', value: `P${Math.round(selected.random_percentile * 100)}` },
      ]} />
      <div className="analysis-grid">
        <section className="chart-panel">
          <div className="section-heading"><h2>累计盈亏</h2><p>系统策略与随机基准均值</p></div>
          <svg viewBox="0 0 760 270" role="img" aria-label="累计收益曲线，系统与随机策略均为负收益">
            {[40, 90, 140, 190, 240].map((y) => <line x1="44" y1={y} x2="740" y2={y} key={y} className="chart-grid" />)}
            <polyline points="44,52 110,68 176,86 242,95 308,118 374,133 440,149 506,171 572,184 638,211 704,228 740,237" className="chart-line chart-line--random" />
            <polyline points="44,52 110,61 176,78 242,83 308,105 374,115 440,132 506,146 572,158 638,181 704,193 740,202" className="chart-line chart-line--model" />
            <text x="52" y="32">¥0</text><text x="52" y="260">-¥3,000</text>
          </svg>
          <div className="chart-legend"><span><i className="legend-model" />{modelLabel(model)}</span><span><i className="legend-random" />随机基准均值</span></div>
        </section>
        <section className="sensitivity-panel">
          <div className="section-heading"><h2>大奖敏感性</h2><p>剔除极端中奖后的收益</p></div>
          <dl>
            <div><dt>完整投资回报率（ROI）</dt><dd>{percent(selected.roi)}</dd></div>
            <div><dt>剔除最大单次中奖</dt><dd>{percent(selected.roi_excluding_largest)}</dd></div>
            <div><dt>剔除奖金最高的1%</dt><dd>{percent(selected.roi_excluding_top_1pct)}</dd></div>
            <div><dt>剔除大奖后投资回报率</dt><dd>{percent(selected.non_jackpot_roi)}</dd></div>
          </dl>
          <p className="negative-note">当前结果仍为负收益，且未达到随机 P95，不支持“稳定优势”结论。</p>
        </section>
      </div>
      <section className="table-section">
        <div className="section-heading"><h2>模型公平比较</h2><p>相同区间、预算、投注频率与原子注成本</p></div>
        <div className="table-scroll"><table><thead><tr><th>模型</th><th>投入</th><th>奖金</th><th>净利润</th><th>投资回报率（ROI）</th><th>相对随机超额ROI</th><th>最大回撤</th><th>随机基准百分位</th></tr></thead><tbody>
          {windowRows.map((row) => <tr className={row.model === model ? 'is-selected' : ''} onClick={() => setModel(row.model)} key={`${row.period}-${row.model}`}><th>{modelLabel(row.model)}</th><td>{money(row.total_cost)}</td><td>{money(row.total_prize)}</td><td>{money(row.net_profit)}</td><td>{percent(row.roi)}</td><td>{percent(row.excess_roi)}</td><td>{money(-row.max_drawdown)}</td><td>P{Math.round(row.random_percentile * 100)}</td></tr>)}
        </tbody></table></div>
      </section>
    </div>
  )
}
