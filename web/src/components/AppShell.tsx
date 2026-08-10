import { BarChart3, Database, FlaskConical, Home, ShieldCheck, TicketCheck } from 'lucide-react'
import type { NavigationKey } from '../types'

const items: { key: NavigationKey; label: string; icon: typeof Home }[] = [
  { key: 'home', label: '首页', icon: Home },
  { key: 'backtest', label: '回测', icon: BarChart3 },
  { key: 'research', label: '研究', icon: FlaskConical },
  { key: 'bets', label: '我的投注', icon: TicketCheck },
  { key: 'validation', label: '验证', icon: ShieldCheck },
]

type Props = {
  active: NavigationKey
  onNavigate: (key: NavigationKey) => void
  children: React.ReactNode
}

export function AppShell({ active, onNavigate, children }: Props) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => onNavigate('home')} aria-label="返回首页">
          <span className="brand__mark" aria-hidden="true"><Database size={18} /></span>
          <span>大乐透长期收益优化系统</span>
        </button>
        <nav className="desktop-nav" aria-label="主要导航">
          {items.map(({ key, label }) => (
            <button className={active === key ? 'is-active' : ''} onClick={() => onNavigate(key)} key={key}>{label}</button>
          ))}
        </nav>
        <span className="version">V1.0.0</span>
      </header>
      <main>{children}</main>
      <footer className="risk-footer">本系统用于概率统计、组合优化及策略回测研究，不保证中奖或盈利。彩票开奖结果具有随机性，请严格控制投注金额。</footer>
      <nav className="bottom-nav" aria-label="移动端导航">
        {items.map(({ key, label, icon: Icon }) => (
          <button className={active === key ? 'is-active' : ''} onClick={() => onNavigate(key)} key={key}>
            <Icon size={21} strokeWidth={active === key ? 2.3 : 1.8} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}

