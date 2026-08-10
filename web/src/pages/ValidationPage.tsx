import { CheckCircle2, Clock3, LockKeyhole, ShieldAlert } from 'lucide-react'
import type { AppData } from '../types'

export function ValidationPage({ data }: { data: AppData }) {
  const stages = [
    { title: 'Training', icon: CheckCircle2, state: '完成', text: '模型训练与特征工程，只使用训练区数据。' },
    { title: 'Validation', icon: CheckCircle2, state: '完成', text: 'Rolling-origin 参数比较和随机基准筛选。' },
    { title: 'Locked Holdout', icon: LockKeyhole, state: '已锁定', text: 'V1 参数冻结后仅验收一次；结果无论好坏都永久保存。' },
    { title: 'Forward Paper', icon: Clock3, state: '收集中', text: '每期开奖前保存版本、号码、预算与 Bet/Skip，开奖后自动结算。' },
  ]
  return (
    <div className="page data-page">
      <header className="page-title"><div><h1>Validation</h1><p>把“开发时看过的数据”和“真正未知的数据”严格分开。</p></div><span>V1.0.0</span></header>
      <section className="validation-flow">{stages.map(({ title, icon: Icon, state, text }) => <article key={title}><Icon size={24} /><div><span>{title}</span><strong>{state}</strong><p>{text}</p></div></article>)}</section>
      <section className="validation-warning"><ShieldAlert size={22} /><div><h2>当前未发现可信的正收益优势</h2><p>“优于随机平均”不等于“显著跑赢随机高分位”；一次大奖也不能证明策略稳定。Forward Paper 样本不足前，不提升到 Validated。</p></div></section>
      <section className="version-table"><div className="section-heading"><h2>版本与不可变记录</h2><p>历史预测不因模型升级而覆盖</p></div><table><thead><tr><th>组件</th><th>版本</th><th>状态</th><th>说明</th></tr></thead><tbody>
        <tr><td>Rule Engine</td><td>{data.latest.ruleVersion}</td><td>Production</td><td>26014期起七奖级规则</td></tr>
        <tr><td>Ensemble</td><td>Ensemble_v1</td><td>Experimental</td><td>未通过长期正收益验证</td></tr>
        <tr><td>Coverage</td><td>coverage_v1</td><td>Candidate</td><td>仅优化组合分散与相关性</td></tr>
        <tr><td>Budget</td><td>budget_v1</td><td>Experimental</td><td>禁止追损，预算上限100元</td></tr>
      </tbody></table></section>
    </div>
  )
}

