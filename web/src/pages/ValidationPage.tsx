import { CheckCircle2, Clock3, LockKeyhole, ShieldAlert } from 'lucide-react'
import type { AppData } from '../types'
import { evidenceStatusLabel } from '../labels'

export function ValidationPage({ data }: { data: AppData }) {
  const stages = [
    { title: '训练阶段', icon: CheckCircle2, state: '完成', text: '模型训练与特征工程，只使用训练区数据。' },
    { title: '验证阶段', icon: CheckCircle2, state: '完成', text: '滚动起点参数比较和随机基准筛选。' },
    { title: '封存测试', icon: LockKeyhole, state: '已锁定', text: 'V1 参数冻结后仅验收一次；结果无论好坏都永久保存。' },
    { title: '前向虚拟验证', icon: Clock3, state: '收集中', text: '每期开奖前保存版本、号码、预算与投注/跳过判断，开奖后自动结算。' },
  ]
  return (
    <div className="page data-page">
      <header className="page-title"><div><h1>策略验证</h1><p>把“开发时看过的数据”和“真正未知的数据”严格分开。</p></div><span>{data.version}</span></header>
      <section className="validation-flow">{stages.map(({ title, icon: Icon, state, text }) => <article key={title}><Icon size={24} /><div><span>{title}</span><strong>{state}</strong><p>{text}</p></div></article>)}</section>
      <section className="validation-warning"><ShieldAlert size={22} /><div><h2>当前未发现可信的正收益优势</h2><p>“优于随机平均”不等于“显著跑赢随机高分位”；一次大奖也不能证明策略稳定。前向虚拟验证样本不足前，不提升为已验证策略。</p></div></section>
      <section className="version-table"><div className="section-heading"><h2>版本与不可变记录</h2><p>历史预测不因模型升级而覆盖</p></div><table><thead><tr><th>组件</th><th>版本</th><th>状态</th><th>说明</th></tr></thead><tbody>
        <tr><td>规则引擎</td><td>{data.latest.ruleVersion}</td><td>生产使用</td><td>26014期起七奖级规则</td></tr>
        <tr><td>集成模型</td><td>Ensemble_v1</td><td>实验阶段</td><td>未通过长期正收益验证</td></tr>
        <tr><td>组合覆盖</td><td>atomic_compare_v1.1</td><td>候选阶段</td><td>仅优化组合分散与相关性</td></tr>
        <tr><td>预算 / 智能推荐</td><td>{data.recommendation.strategyVersion}</td><td>{evidenceStatusLabel(data.recommendation.evidence.status)}</td><td>真实策略证据缺失或不足时建议不投注 / 0元</td></tr>
      </tbody></table></section>
    </div>
  )
}
