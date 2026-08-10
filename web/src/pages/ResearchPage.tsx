import type { AppData } from '../types'

const front = [
  ['03', 0.82, 6], ['07', 0.75, 1], ['12', 0.69, 4], ['14', 0.62, 8], ['26', 0.58, 2],
  ['31', 0.53, 11], ['08', 0.48, 13], ['19', 0.44, 5], ['22', 0.4, 17], ['35', 0.36, 9],
]

export function ResearchPage({ data }: { data: AppData }) {
  return (
    <div className="page data-page">
      <header className="page-title"><div><h1>数据研究</h1><p>统计特征默认无效，只有经置换检验、自助法与假发现率（FDR）校正后才可能进入候选策略。</p></div><span>{data.history.count} 期已验证数据</span></header>
      <section className="research-methods">
        <div><strong>500 / 1000</strong><span>置换检验次数</span></div>
        <div><strong>50</strong><span>假设检验数量</span></div>
        <div><strong>0</strong><span>FDR 后显著特征</span></div>
        <div><strong>实验阶段</strong><span>当前策略评级</span></div>
      </section>
      <div className="research-layout">
        <section>
          <div className="section-heading"><h2>前区相对排序</h2><p>模型评分，不是真实开奖概率</p></div>
          <div className="score-list">{front.map(([number, score, omission]) => <div key={number as string}><strong>{number}</strong><span><i style={{ width: `${Number(score) * 100}%` }} /></span><em>{Number(score).toFixed(2)}</em><small>遗漏 {omission}</small></div>)}</div>
        </section>
        <section className="hypothesis-table">
          <div className="section-heading"><h2>反伪规律检验</h2><p>示例结果</p></div>
          <table><thead><tr><th>特征</th><th>原始 p</th><th>FDR 后</th><th>结论</th></tr></thead><tbody>
            <tr><td>30期热号</td><td>0.082</td><td>0.41</td><td>不显著</td></tr>
            <tr><td>遗漏</td><td>0.19</td><td>0.63</td><td>不显著</td></tr>
            <tr><td>前区和值</td><td>0.046</td><td>0.31</td><td>不显著</td></tr>
            <tr><td>号码对互信息（PMI）</td><td>0.012</td><td>0.18</td><td>不显著</td></tr>
          </tbody></table>
          <p>随机打乱序列中也会频繁出现“漂亮规律”。未通过多重检验校正的特征不得进入生产推荐。</p>
        </section>
      </div>
      <section className="crowding-section"><h2>选号拥挤度 / 流行度代理</h2><p>生日型、等差、对称、整齐尾数等仅用于研究潜在奖池分享风险。它不会提高开奖号码命中率，也不代表真实投注人数。</p></section>
    </div>
  )
}
