import { useMemo, useState } from 'react'

type Bet = { issue: string; numbers: string; cost: number; purchasedAt: string }

export function MyBetsPage() {
  const [bets, setBets] = useState<Bet[]>(() => {
    try { return JSON.parse(localStorage.getItem('dlt-real-bets-v1') ?? '[]') as Bet[] } catch { return [] }
  })
  const [issue, setIssue] = useState('26090')
  const [numbers, setNumbers] = useState('')
  const [cost, setCost] = useState(20)
  const total = useMemo(() => bets.reduce((sum, bet) => sum + bet.cost, 0), [bets])

  function addBet(event: React.FormEvent) {
    event.preventDefault()
    if (!numbers.trim() || cost < 0 || cost > 100) return
    const next = [{ issue, numbers: numbers.trim(), cost, purchasedAt: new Date().toISOString() }, ...bets]
    setBets(next)
    localStorage.setItem('dlt-real-bets-v1', JSON.stringify(next))
    setNumbers('')
  }

  return (
    <div className="page data-page">
      <header className="page-title"><div><h1>My Bets</h1><p>只记录真实购买；系统推荐和 Paper Bet 不计入实际盈亏。</p></div><span>累计实际投入 ¥{total}</span></header>
      <div className="bets-layout">
        <form className="bet-form" onSubmit={addBet}>
          <h2>记录实际投注</h2>
          <label>期号<input value={issue} onChange={(event) => setIssue(event.target.value)} inputMode="numeric" /></label>
          <label>号码<textarea value={numbers} onChange={(event) => setNumbers(event.target.value)} placeholder="03 11 18 24 33 + 04 09" /></label>
          <label>实际金额（0–100元）<input type="number" min="0" max="100" value={cost} onChange={(event) => setCost(Number(event.target.value))} /></label>
          <button type="submit">保存真实投注</button>
          <p>本地浏览器保存仅用于个人记录；静态站点不会上传隐私数据。</p>
        </form>
        <section className="bet-history"><h2>真实投注记录</h2>{bets.length === 0 ? <div className="empty-state"><strong>还没有真实投注</strong><p>未购买的彩票不会被算入“实际盈利”。</p></div> : bets.map((bet) => <article key={`${bet.issue}-${bet.purchasedAt}`}><div><strong>第 {bet.issue} 期</strong><span>{new Date(bet.purchasedAt).toLocaleString('zh-CN')}</span></div><p>{bet.numbers}</p><em>¥{bet.cost}</em></article>)}</section>
      </div>
    </div>
  )
}

