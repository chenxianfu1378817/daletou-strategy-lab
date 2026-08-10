import { useEffect, useState } from 'react'
import { AppShell } from './components/AppShell'
import { fallbackData, isStale, loadData } from './data'
import { BacktestPage } from './pages/BacktestPage'
import { HomePage } from './pages/HomePage'
import { MyBetsPage } from './pages/MyBetsPage'
import { ResearchPage } from './pages/ResearchPage'
import { ValidationPage } from './pages/ValidationPage'
import type { AppData, NavigationKey } from './types'

function routeFromHash(): NavigationKey {
  const value = window.location.hash.replace('#/', '')
  return ['home', 'backtest', 'research', 'bets', 'validation'].includes(value) ? value as NavigationKey : 'home'
}

export default function App() {
  const [active, setActive] = useState<NavigationKey>(routeFromHash)
  const [data, setData] = useState<AppData>(fallbackData)
  const [fallback, setFallback] = useState(false)

  useEffect(() => {
    loadData().then((result) => { setData(result.data); setFallback(result.fallback) })
    const onHashChange = () => setActive(routeFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  function navigate(key: NavigationKey) {
    window.location.hash = `/${key}`
    setActive(key)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <AppShell active={active} onNavigate={navigate}>
      {active === 'home' && <HomePage data={data} stale={isStale(data.generatedAt)} fallback={fallback} />}
      {active === 'backtest' && <BacktestPage data={data} />}
      {active === 'research' && <ResearchPage data={data} />}
      {active === 'bets' && <MyBetsPage />}
      {active === 'validation' && <ValidationPage data={data} />}
    </AppShell>
  )
}

